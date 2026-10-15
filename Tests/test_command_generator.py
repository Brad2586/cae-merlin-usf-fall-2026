import json
import tempfile
import unittest
from pathlib import Path

from Pipeline.command_registry import CommandRegistry
from Tools.command_generator import add_command


class CommandGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.variables_path = self.root / "variables.xml"
        self.commands_path = self.root / "voice_commands.json"
        self.variables_path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<variables><variable name="MALF_IF.TOGGLE_REQ" '
            'type="int32" common_name="Malfunction Toggle Request" /></variables>\n',
            encoding="utf-8",
        )
        self.commands_path.write_text('{"commands": []}\n', encoding="utf-8")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_existing_variable_command_matches_voice_transcript(self):
        add_command(
            name="Activate Engine 5 Fire",
            variable="MALF_IF.TOGGLE_REQ",
            raw_value="335",
            phrases=["activate engine 5 fire malfunction"],
            variables_path=self.variables_path,
            commands_path=self.commands_path,
        )

        registry = CommandRegistry(self.commands_path)
        self.assertEqual(
            registry.match("Activate engine 5 fire malfunction!"),
            {
                "Type": "command",
                "command_name": "Activate Engine 5 Fire",
                "parameters_keys": ["MALF_IF.TOGGLE_REQ"],
                "parameters_values": [335],
            },
        )

    def test_new_array_variable_and_indices_are_generated(self):
        add_command(
            name="Enable Test Failure",
            variable="TEST.FAILURES",
            raw_value="true",
            phrases=["enable test failure"],
            variable_type="boolean",
            common_name="Test Failures",
            dimensions=[4],
            indices=[2],
            variables_path=self.variables_path,
            commands_path=self.commands_path,
        )

        xml = self.variables_path.read_text(encoding="utf-8")
        self.assertIn('name="TEST.FAILURES"', xml)
        self.assertIn('dims="4"', xml)

        output = CommandRegistry(self.commands_path).match("enable test failure")
        self.assertEqual(output["parameters_values"], [True])
        self.assertEqual(
            output["parameters_meta"],
            [{"key": "TEST.FAILURES", "indices": [2]}],
        )

    def test_duplicate_normalized_phrase_is_rejected(self):
        arguments = {
            "name": "First",
            "variable": "MALF_IF.TOGGLE_REQ",
            "raw_value": "1",
            "phrases": ["set test"],
            "variables_path": self.variables_path,
            "commands_path": self.commands_path,
        }
        add_command(**arguments)
        arguments.update(name="Second", raw_value="2", phrases=["Set test!"])

        with self.assertRaisesRegex(ValueError, "already belongs"):
            add_command(**arguments)

        data = json.loads(self.commands_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data["commands"]), 1)

    def test_mapping_commands_use_fast_runtime_path(self):
        mapping_path = self.root / "mapping.xml"
        mapping_path.write_text(
            "<mappings><command>"
            "<name>Enable Total Freeze</name>"
            "<variable>MALF_IF.TOGGLE_REQ</variable>"
            "<value>1</value>"
            "</command></mappings>",
            encoding="utf-8",
        )

        registry = CommandRegistry(self.commands_path, mapping_path=mapping_path)
        self.assertEqual(
            registry.match("turn on total freeze"),
            {
                "Type": "command",
                "command_name": "Enable Total Freeze",
                "parameters_keys": ["MALF_IF.TOGGLE_REQ"],
                "parameters_values": [1],
            },
        )


if __name__ == "__main__":
    unittest.main()
