"""Runtime registry for user-defined voice commands."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def normalize_phrase(phrase: str) -> str:
    """Normalize speech text so punctuation and capitalization do not matter."""
    return " ".join(re.findall(r"[a-z0-9]+", phrase.casefold()))


_ENGINE_FIRE_NAME = re.compile(
    r"^(Activate|Deactivate) Engine (\d+) Fire Malfunction$"
)
_ENGINE_MALFUNCTION_NAME = re.compile(
    r"^(Activate|Deactivate) Engine (\d+) Malfunction$"
)


_NUMBER_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four"}


def _number_forms(engine_number: str) -> list[str]:
    forms = [engine_number]
    word = _NUMBER_WORDS.get(engine_number)
    if word:
        forms.append(word)
    return forms


def engine_fire_phrases(engine_number: str, enabled: bool) -> list[str]:
    """Spoken forms for one engine's flameout flag."""
    phrases = []
    for number in _number_forms(engine_number):
        if enabled:
            phrases.extend([
                f"activate engine {number} fire malfunction",
                f"activate engine fire malfunction {number}",
                f"engine {number} fire malfunction",
                f"engine fire malfunction {number}",
                f"activate engine {number} flameout",
                f"engine {number} flameout",
            ])
        else:
            phrases.extend([
                f"deactivate engine {number} fire malfunction",
                f"deactivate engine fire malfunction {number}",
                f"clear engine {number} fire malfunction",
                f"deactivate engine {number} flameout",
                f"engine {number} flameout off",
            ])
    return phrases


def engine_malfunction_phrases(engine_number: str, enabled: bool) -> list[str]:
    """Spoken forms for one engine's instructor malfunction code."""
    phrases = []
    for number in _number_forms(engine_number):
        if enabled:
            phrases.extend([
                f"activate engine {number} malfunction",
                f"activate engine malfunction {number}",
                f"engine {number} malfunction",
                f"engine malfunction {number}",
            ])
        else:
            phrases.extend([
                f"deactivate engine {number} malfunction",
                f"deactivate engine malfunction {number}",
                f"clear engine {number} malfunction",
                f"engine {number} malfunction off",
            ])
    return phrases


def mapping_phrase_variants(command_name: str) -> list[str]:
    """Create common voice phrasings for a mapping.xml command name."""
    phrases = [command_name]
    substitutions = {
        "Activate ": ("Enable ", "Turn on ", "Trigger "),
        "Deactivate ": ("Disable ", "Turn off ", "Clear "),
        "Enable ": ("Turn on ",),
        "Disable ": ("Turn off ",),
    }
    for prefix, replacements in substitutions.items():
        if command_name.startswith(prefix):
            remainder = command_name[len(prefix):]
            phrases.extend(replacement + remainder for replacement in replacements)
            if remainder.endswith(" Freeze"):
                subject = remainder[:-len(" Freeze")]
                if prefix == "Enable ":
                    phrases.extend((remainder + " on", "Freeze " + subject))
                elif prefix == "Disable ":
                    phrases.extend((remainder + " off", "Unfreeze " + subject))
            break
    return phrases


class CommandRegistry:
    """Load and match generated commands without requiring LLM retraining."""

    def __init__(self, path: str | Path, mapping_path: str | Path | None = None):
        self.path = Path(path)
        self.mapping_path = Path(mapping_path) if mapping_path else None
        self.commands: list[dict[str, Any]] = []
        self._phrase_index: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        if not self.path.exists():
            self.commands = []
            self._phrase_index = {}
            return

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        commands = data.get("commands", [])
        if not isinstance(commands, list):
            raise ValueError(f"'commands' must be a list in {self.path}")

        phrase_index: dict[str, dict[str, Any]] = {}
        for command in commands:
            if not isinstance(command, dict):
                raise ValueError(f"Each command must be an object in {self.path}")
            if not command.get("variable") or "value" not in command:
                raise ValueError("Each generated command needs a variable and value")

            for phrase in command.get("phrases", []):
                normalized = normalize_phrase(str(phrase))
                if not normalized:
                    continue
                if normalized in phrase_index:
                    raise ValueError(f"Duplicate generated command phrase: {phrase!r}")
                phrase_index[normalized] = command

        # Every command name in mapping.xml is also an immediate voice phrase.
        # This bypasses the LLM for standard simulator commands while generated
        # commands above retain priority if a phrase intentionally overlaps.
        flame_enable_aliases: list[str] = []
        flame_disable_aliases: list[str] = []
        if self.mapping_path and self.mapping_path.exists():
            mapping_root = ET.parse(self.mapping_path).getroot()
            for element in mapping_root.iter("command"):
                name = (element.findtext("name") or "").strip()
                variable = (element.findtext("variable") or "").strip()
                raw_value = (element.findtext("value") or "").strip()
                alias = (element.findtext("alias") or "").strip()
                action = (element.findtext("action") or "").strip().lower()
                if not name or not variable or not raw_value:
                    continue
                try:
                    value: Any = int(raw_value)
                except ValueError:
                    try:
                        value = float(raw_value)
                    except ValueError:
                        value = raw_value

                phrases = mapping_phrase_variants(name)
                fire_name = _ENGINE_FIRE_NAME.match(name)
                malfunction_name = _ENGINE_MALFUNCTION_NAME.match(name)
                if fire_name and alias:
                    enabled = fire_name.group(1) == "Activate"
                    phrases.extend(engine_fire_phrases(fire_name.group(2), enabled))
                    mapped_command = {
                        "name": name,
                        "phrases": phrases,
                        "variable": alias,
                        "value": enabled,
                    }
                    if enabled:
                        flame_enable_aliases.append(alias)
                    else:
                        flame_disable_aliases.append(alias)
                else:
                    if malfunction_name:
                        enabled = malfunction_name.group(1) == "Activate"
                        phrases.extend(
                            engine_malfunction_phrases(
                                malfunction_name.group(2), enabled
                            )
                        )
                    mapped_command = {
                        "name": name,
                        "phrases": phrases,
                        "variable": variable,
                        "value": value,
                    }
                    if action:
                        mapped_command["action"] = action
                for phrase in mapped_command["phrases"]:
                    phrase_index.setdefault(normalize_phrase(phrase), mapped_command)

            self._add_flameout_group(
                phrase_index,
                "Activate Engine Fire Malfunction",
                [
                    "activate engine fire malfunction",
                    "activate fire malfunction",
                    "turn on engine fire malfunction",
                    "engine fire malfunction on",
                    "activate engine flameout",
                ],
                flame_enable_aliases,
                True,
            )
            self._add_flameout_group(
                phrase_index,
                "Deactivate Engine Fire Malfunction",
                [
                    "deactivate engine fire malfunction",
                    "deactivate fire malfunction",
                    "turn off engine fire malfunction",
                    "engine fire malfunction off",
                    "clear engine fire malfunction",
                ],
                flame_disable_aliases,
                False,
            )

        self.commands = commands
        self._phrase_index = phrase_index

    @staticmethod
    def _add_flameout_group(phrase_index, name, phrases, aliases, enabled):
        """Map an engine-less fire phrase onto every flameout flag."""
        if len(aliases) != 4:
            return
        grouped_command = {
            "name": name,
            "phrases": phrases,
            "parameters": [
                {"variable": alias, "value": enabled} for alias in aliases
            ],
        }
        for phrase in phrases:
            phrase_index.setdefault(normalize_phrase(phrase), grouped_command)

    def match(self, transcript: str) -> dict[str, Any] | None:
        """Return parser-compatible command JSON for an exact spoken phrase."""
        command = self._phrase_index.get(normalize_phrase(transcript))
        if command is None:
            return None

        parameters = command.get("parameters")
        if parameters:
            return {
                "Type": "command",
                "command_name": command.get("name", "Generated command"),
                "parameters_keys": [item["variable"] for item in parameters],
                "parameters_values": [item["value"] for item in parameters],
            }

        output: dict[str, Any] = {
            "Type": "command",
            "command_name": command.get("name", "Generated command"),
            "parameters_keys": [command["variable"]],
            "parameters_values": [command["value"]],
        }
        indices = command.get("indices")
        if indices is not None:
            output["parameters_meta"] = [
                {"key": command["variable"], "indices": indices}
            ]
        return output
