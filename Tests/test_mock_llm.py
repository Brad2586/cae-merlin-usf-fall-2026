import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Pipeline"))

from mock_llm import DatasetMockModel


class DatasetMockModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = DatasetMockModel(
            PROJECT_ROOT / "DataSet" / "Strict" / "Data_Strict.jsonl",
            threshold=0.78,
        )

    def test_exact_command_returns_expected_json(self):
        output = self.model.match("activate engine 1 fire malfunction")

        self.assertEqual(output["Type"], "command")
        self.assertEqual(output["parameters_keys"], ["ENGINE_1_MALF"])
        self.assertEqual(output["parameters_values"], ["true"])

    def test_minor_transcription_error_can_fuzzy_match(self):
        output = self.model.match("activate engine 1 fire malfuncton")

        self.assertEqual(output["Type"], "command")
        self.assertEqual(output["parameters_values"], ["true"])

    def test_deactivate_does_not_flip_to_activate(self):
        output = self.model.match("deactivate engine 1 fire malfuncton")

        self.assertEqual(output["Type"], "command")
        self.assertEqual(output["parameters_values"], ["false"])

    def test_unknown_command_fails_closed(self):
        output = self.model.match("order pizza and open the hangar")

        self.assertEqual(output["Type"], "error")

    def test_missing_entity_does_not_match_another_freeze_type(self):
        output = self.model.match("turn altitude freeze on")

        self.assertEqual(output["Type"], "error")

    def test_llama_compatible_interface_extracts_prompt_input(self):
        result = self.model(
            "input: activate engine 1 fire malfunction\noutput:",
            max_tokens=150,
            temperature=0.0,
            echo=False,
        )
        output = json.loads(result["choices"][0]["text"])

        self.assertEqual(output["parameters_keys"], ["ENGINE_1_MALF"])
        self.assertTrue(result["usage"]["mock"])

    def test_custom_command_overrides_dataset_phrase(self):
        registry = {
            "commands": [
                {
                    "id": "test_override",
                    "enabled": True,
                    "phrases": ["activate engine 1 fire malfunction"],
                    "parameters_keys": ["ENGINE_1_MALF"],
                    "parameters_values": ["false"],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "mock_commands.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            model = DatasetMockModel(
                PROJECT_ROOT / "DataSet" / "Strict" / "Data_Strict.jsonl",
                custom_commands_path=registry_path,
            )

            output = model.match("activate engine 1 fire malfunction")

        self.assertEqual(output["parameters_values"], ["false"])
        self.assertEqual(model.custom_command_count, 1)

    def test_disabled_custom_command_is_not_loaded(self):
        registry = {
            "commands": [
                {
                    "id": "disabled_diagnostic",
                    "enabled": False,
                    "phrases": ["run custom diagnostic sequence"],
                    "parameters_keys": ["DIAGNOSTIC"],
                    "parameters_values": ["true"],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "mock_commands.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            model = DatasetMockModel(
                PROJECT_ROOT / "DataSet" / "Strict" / "Data_Strict.jsonl",
                custom_commands_path=registry_path,
            )

            output = model.match("run custom diagnostic sequence")

        self.assertEqual(output["Type"], "error")
        self.assertEqual(model.custom_command_count, 0)


if __name__ == "__main__":
    unittest.main()

