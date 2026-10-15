"""Interactive generator for simulator variables and voice commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_VARIABLES_PATH = PROJECT_ROOT / "config" / "variables.xml"
DEFAULT_COMMANDS_PATH = PROJECT_ROOT / "config" / "voice_commands.json"

SUPPORTED_TYPES = {
    "char",
    "int8",
    "int16",
    "int32",
    "int64",
    "float",
    "double",
    "pointer",
    "boolean",
    "integer",
}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _load_variables(path: Path) -> tuple[ET.ElementTree, dict[str, ET.Element]]:
    tree = ET.parse(path)
    variables = {
        element.get("name"): element
        for element in tree.getroot().iter("variable")
        if element.get("name")
    }
    return tree, variables


def _load_commands(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"commands": []}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not isinstance(data.get("commands"), list):
        raise ValueError(f"Invalid command registry: {path}")
    return data


def _parse_int_list(raw: str | None, field_name: str) -> list[int] | None:
    if raw is None or not raw.strip():
        return None
    try:
        values = [int(value) for value in raw.replace(",", " ").split()]
    except ValueError as exc:
        raise ValueError(f"{field_name} must contain whole numbers") from exc
    if any(value < 0 for value in values):
        raise ValueError(f"{field_name} cannot contain negative numbers")
    return values


def parse_value(raw: str, variable_type: str) -> Any:
    value = raw.strip()
    if variable_type == "boolean":
        lowered = value.casefold()
        if lowered in {"true", "1", "on", "yes", "enable", "enabled"}:
            return True
        if lowered in {"false", "0", "off", "no", "disable", "disabled"}:
            return False
        raise ValueError("Boolean values must be true/false, on/off, or 1/0")

    if variable_type in {"int8", "int16", "int32", "int64", "integer", "pointer"}:
        parsed = int(value)
        ranges = {
            "int8": (-128, 127),
            "int16": (-32768, 32767),
            "int32": (-2147483648, 2147483647),
            "int64": (-9223372036854775808, 9223372036854775807),
        }
        if variable_type == "pointer" and parsed < 0:
            raise ValueError("Pointer values cannot be negative")
        if variable_type in ranges:
            low, high = ranges[variable_type]
            if not low <= parsed <= high:
                raise ValueError(f"{variable_type} value must be between {low} and {high}")
        return parsed

    if variable_type in {"float", "double"}:
        return float(value)

    if variable_type == "char":
        if not value:
            raise ValueError("Character/string values cannot be empty")
        return value

    raise ValueError(f"Unsupported variable type: {variable_type}")


def add_command(
    *,
    name: str,
    variable: str,
    raw_value: str,
    phrases: list[str],
    variable_type: str | None = None,
    common_name: str | None = None,
    dimensions: list[int] | None = None,
    indices: list[int] | None = None,
    variables_path: Path = DEFAULT_VARIABLES_PATH,
    commands_path: Path = DEFAULT_COMMANDS_PATH,
) -> dict[str, Any]:
    name = name.strip()
    variable = variable.strip()
    phrases = list(dict.fromkeys(phrase.strip() for phrase in phrases if phrase.strip()))
    if not name or not variable or not phrases:
        raise ValueError("Command name, variable name, and at least one phrase are required")

    tree, variables = _load_variables(variables_path)
    existing_variable = variables.get(variable)
    new_variable = existing_variable is None

    if existing_variable is not None:
        resolved_type = (existing_variable.get("type") or "").casefold()
        declared_dims = _parse_int_list(existing_variable.get("dims"), "dimensions") or []
        if variable_type and variable_type.casefold() != resolved_type:
            raise ValueError(
                f"{variable} already exists as {resolved_type}, not {variable_type}"
            )
    else:
        if not variable_type:
            raise ValueError("A type is required when adding a new variable")
        resolved_type = variable_type.casefold()
        if resolved_type not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported type: {resolved_type}")
        declared_dims = dimensions or []

    if indices is not None:
        if len(indices) != len(declared_dims):
            raise ValueError(
                f"indices must contain {len(declared_dims)} value(s) for {variable}"
            )
        for index, size in zip(indices, declared_dims):
            if index >= size:
                raise ValueError(f"Index {index} is outside a dimension of size {size}")
    elif declared_dims:
        raise ValueError(f"{variable} is an array; indices are required")

    value = parse_value(raw_value, resolved_type)
    registry = _load_commands(commands_path)

    from Pipeline.command_registry import normalize_phrase

    existing_phrases = {
        normalize_phrase(phrase)
        for command in registry["commands"]
        for phrase in command.get("phrases", [])
    }
    duplicates = [
        phrase for phrase in phrases if normalize_phrase(phrase) in existing_phrases
    ]
    if duplicates:
        raise ValueError(f"Phrase already belongs to another command: {duplicates[0]!r}")

    command: dict[str, Any] = {
        "name": name,
        "phrases": phrases,
        "variable": variable,
        "value": value,
    }
    if indices is not None:
        command["indices"] = indices

    if new_variable:
        attributes = {
            "name": variable,
            "type": resolved_type,
            "common_name": (common_name or name).strip(),
        }
        if declared_dims:
            attributes["dims"] = " ".join(str(size) for size in declared_dims)
        ET.SubElement(tree.getroot(), "variable", attributes)

    registry["commands"].append(command)

    # Validate both changes before writing either file.
    json_content = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    if new_variable:
        ET.indent(tree, space="  ")
        xml_content = ET.tostring(
            tree.getroot(), encoding="unicode", xml_declaration=False
        )
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content + "\n"
        _atomic_write(variables_path, xml_content)
    _atomic_write(commands_path, json_content)
    return command


def _prompt(current: str | None, label: str) -> str:
    if current is not None:
        return current
    return input(f"{label}: ").strip()


def interactive_add(args: argparse.Namespace) -> dict[str, Any]:
    _, variables = _load_variables(args.variables_path)
    print("\nAvailable variables:")
    for variable_name in sorted(variables):
        print(f"  {variable_name} ({variables[variable_name].get('type')})")
    print("Enter a new variable name to create it.\n")

    name = _prompt(args.name, "Command name (example: Activate Engine 5 Fire)")
    variable = _prompt(args.variable, "Simulator variable name")
    existing = variables.get(variable)

    variable_type = args.variable_type
    common_name = args.common_name
    dimensions = _parse_int_list(args.dimensions, "dimensions")
    if existing is None:
        variable_type = _prompt(
            variable_type,
            "Variable type (boolean, int32, float, double, char, etc.)",
        )
        common_name = _prompt(common_name, "Human-readable variable name")
        if args.dimensions is None:
            dimensions = _parse_int_list(
                input("Array dimensions (blank for scalar): "), "dimensions"
            )

    value = _prompt(args.value, "Value to send")
    phrase_values = args.phrase or []
    if not phrase_values:
        phrase_values = [
            phrase.strip()
            for phrase in input("Spoken phrases (separate with |): ").split("|")
            if phrase.strip()
        ]

    declared_dims = (
        dimensions
        if existing is None
        else (_parse_int_list(existing.get("dims"), "dimensions") or [])
    )
    indices = _parse_int_list(args.indices, "indices")
    if declared_dims and args.indices is None:
        indices = _parse_int_list(
            input("Zero-based array indices (space-separated): "), "indices"
        )

    return add_command(
        name=name,
        variable=variable,
        raw_value=value,
        phrases=phrase_values,
        variable_type=variable_type,
        common_name=common_name,
        dimensions=dimensions,
        indices=indices,
        variables_path=args.variables_path,
        commands_path=args.commands_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add a simulator variable and voice command without editing code."
    )
    parser.add_argument("--name", help="Human-readable command name")
    parser.add_argument("--variable", help="Host variable name")
    parser.add_argument("--value", help="Fixed value sent when the command is spoken")
    parser.add_argument(
        "--phrase", action="append", help="Accepted spoken phrase (repeatable)"
    )
    parser.add_argument("--type", dest="variable_type", help="Type for a new variable")
    parser.add_argument("--common-name", help="Human-readable name for a new variable")
    parser.add_argument("--dimensions", help="Sizes for a new array, e.g. '4 2'")
    parser.add_argument("--indices", help="Zero-based target indices, e.g. '0 1'")
    parser.add_argument(
        "--variables-path", type=Path, default=DEFAULT_VARIABLES_PATH, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--commands-path", type=Path, default=DEFAULT_COMMANDS_PATH, help=argparse.SUPPRESS
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        command = interactive_add(args)
    except (ValueError, OSError, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"\nCommand was not added: {exc}")
        return 1

    print(f"\nAdded '{command['name']}'.")
    print("Restart Pipeline/main.py, then say any configured phrase after the wake word.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
