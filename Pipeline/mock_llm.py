"""Deterministic stand-in for the unavailable GGUF command models.

The mock loads Merlin's existing JSONL datasets and exposes the same callable
interface as llama_cpp.Llama. It is intentionally conservative: an input must
match a known training phrase closely enough or it returns an error response.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


_ENTITY_TOKENS = {
    "airspeed",
    "altitude",
    "approach",
    "attitude",
    "engine",
    "fire",
    "flight",
    "fuel",
    "heading",
    "malfunction",
    "position",
    "total",
}


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _polarity(text: str) -> str | None:
    tokens = set(_normalize(text).split())
    if tokens & {"deactivate", "disable", "disabled", "off", "false"}:
        return "off"
    if tokens & {"activate", "enable", "enabled", "on", "true"}:
        return "on"
    return None


class DatasetMockModel:
    """Return dataset outputs using exact or guarded fuzzy phrase matching."""

    def __init__(
        self,
        dataset_path: str | Path,
        threshold: float = 0.78,
        custom_commands_path: str | Path | None = None,
    ):
        self.dataset_path = Path(dataset_path)
        self.custom_commands_path = (
            Path(custom_commands_path) if custom_commands_path else None
        )
        self.threshold = threshold
        self._examples: list[tuple[str, dict]] = []
        self._exact: dict[str, dict] = {}
        self.custom_command_count = 0
        self.last_match: tuple[str, float] | None = None
        self._load_custom_commands()
        self._load()

    def _add_example(self, phrase: str, output: dict, override: bool = False) -> None:
        normalized = _normalize(phrase)
        if not normalized:
            return
        self._examples.append((normalized, output))
        if override:
            self._exact[normalized] = output
        else:
            self._exact.setdefault(normalized, output)

    def _load_custom_commands(self) -> None:
        if self.custom_commands_path is None:
            return
        if not self.custom_commands_path.exists():
            raise FileNotFoundError(
                f"Mock command registry not found: {self.custom_commands_path}"
            )

        try:
            with self.custom_commands_path.open("r", encoding="utf-8-sig") as registry:
                data = json.load(registry)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in mock command registry: {self.custom_commands_path}"
            ) from exc

        commands = data.get("commands", [])
        if not isinstance(commands, list):
            raise ValueError("mock_commands.json 'commands' must be a list")

        seen_ids: set[str] = set()
        for position, command in enumerate(commands, start=1):
            if not isinstance(command, dict):
                raise ValueError(f"Mock command #{position} must be an object")

            command_id = str(command.get("id", "")).strip()
            if not command_id:
                raise ValueError(f"Mock command #{position} is missing a non-empty 'id'")
            if command_id in seen_ids:
                raise ValueError(f"Duplicate mock command id: {command_id}")
            seen_ids.add(command_id)

            if command.get("enabled", True) is False:
                continue

            phrases = command.get("phrases")
            if not isinstance(phrases, list) or not phrases:
                raise ValueError(
                    f"Enabled mock command '{command_id}' needs a non-empty phrases list"
                )

            if "output" in command:
                output = command["output"]
                if not isinstance(output, dict) or not output.get("Type"):
                    raise ValueError(
                        f"Mock command '{command_id}' output needs a Type"
                    )
            else:
                keys = command.get("parameters_keys")
                values = command.get("parameters_values")
                if not isinstance(keys, list) or not isinstance(values, list):
                    raise ValueError(
                        f"Mock command '{command_id}' needs parameters_keys and "
                        "parameters_values lists"
                    )
                if len(keys) != len(values) or not keys:
                    raise ValueError(
                        f"Mock command '{command_id}' parameter lists must be "
                        "non-empty and the same length"
                    )
                output = {
                    "Type": "command",
                    "parameters_keys": keys,
                    "parameters_values": values,
                }

            for phrase in phrases:
                if not isinstance(phrase, str) or not phrase.strip():
                    raise ValueError(
                        f"Mock command '{command_id}' contains an invalid phrase"
                    )
                self._add_example(phrase, output, override=True)

            self.custom_command_count += 1

    def _load(self) -> None:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Mock dataset not found: {self.dataset_path}")

        with self.dataset_path.open("r", encoding="utf-8-sig") as dataset:
            for line_number, line in enumerate(dataset, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    phrase = _normalize(str(record["input"]))
                    output = record["output"]
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(
                        f"Invalid mock dataset record at "
                        f"{self.dataset_path}:{line_number}"
                    ) from exc

                if not phrase or not isinstance(output, dict):
                    continue
                self._add_example(phrase, output)

        if not self._examples:
            raise ValueError(f"Mock dataset contains no usable examples: {self.dataset_path}")

    @staticmethod
    def _extract_input(prompt: str) -> str:
        match = re.search(r"(?:^|\n)input:\s*(.*?)(?:\noutput:|$)", prompt, re.I | re.S)
        return match.group(1).strip() if match else prompt.strip()

    def match(self, text: str) -> dict:
        normalized = _normalize(text)
        if normalized in self._exact:
            self.last_match = (normalized, 1.0)
            return self._exact[normalized]

        requested_polarity = _polarity(normalized)
        requested_entities = set(normalized.split()) & _ENTITY_TOKENS
        best_phrase = ""
        best_output = None
        best_score = 0.0

        for phrase, output in self._examples:
            candidate_polarity = _polarity(phrase)
            if (
                requested_polarity is not None
                and candidate_polarity is not None
                and requested_polarity != candidate_polarity
            ):
                continue

            candidate_entities = set(phrase.split()) & _ENTITY_TOKENS
            if requested_entities and not requested_entities.issubset(candidate_entities):
                continue

            score = SequenceMatcher(None, normalized, phrase).ratio()
            if score > best_score:
                best_phrase = phrase
                best_output = output
                best_score = score

        self.last_match = (best_phrase, best_score)
        if best_output is not None and best_score >= self.threshold:
            return best_output

        return {
            "Type": "error",
            "message": (
                "Mock mode could not safely match that command "
                f"(best confidence {best_score:.0%})."
            ),
        }

    def __call__(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.0,
        echo: bool = False,
        **_kwargs,
    ) -> dict:
        del max_tokens, temperature, echo
        requested_input = self._extract_input(prompt)
        output = self.match(requested_input)
        return {
            "choices": [{"text": json.dumps(output, separators=(",", ":"))}],
            "usage": {
                "mock": True,
                "examples": len(self._examples),
                "custom_commands": self.custom_command_count,
            },
        }

    def close(self) -> None:
        pass

