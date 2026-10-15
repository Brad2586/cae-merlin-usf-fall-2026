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
        if self.mapping_path and self.mapping_path.exists():
            mapping_root = ET.parse(self.mapping_path).getroot()
            for element in mapping_root.iter("command"):
                name = (element.findtext("name") or "").strip()
                variable = (element.findtext("variable") or "").strip()
                raw_value = (element.findtext("value") or "").strip()
                if not name or not variable or not raw_value:
                    continue
                try:
                    value: Any = int(raw_value)
                except ValueError:
                    try:
                        value = float(raw_value)
                    except ValueError:
                        value = raw_value
                mapped_command = {
                    "name": name,
                    "phrases": mapping_phrase_variants(name),
                    "variable": variable,
                    "value": value,
                }
                for phrase in mapped_command["phrases"]:
                    phrase_index.setdefault(normalize_phrase(phrase), mapped_command)

        self.commands = commands
        self._phrase_index = phrase_index

    def match(self, transcript: str) -> dict[str, Any] | None:
        """Return parser-compatible command JSON for an exact spoken phrase."""
        command = self._phrase_index.get(normalize_phrase(transcript))
        if command is None:
            return None

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
