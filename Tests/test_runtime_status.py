import json
import tempfile
import unittest
from pathlib import Path

from Pipeline.runtime_status import RuntimeStatus


class RuntimeStatusTests(unittest.TestCase):
    def test_status_and_requested_changes_are_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime_status.json"
            status = RuntimeStatus(path, max_changes=2)
            status.reset_session(active_model="lenient")
            status.update(server_state="connected")
            status.record_command("freeze altitude", "Enable Altitude Freeze")
            status.record_change(
                "MODE_IF.ALT_FRZ_REQ",
                1,
                display_name="Altitude Freeze",
            )

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["active_model"], "lenient")
            self.assertEqual(saved["server_state"], "connected")
            self.assertEqual(saved["last_transcription"], "freeze altitude")
            self.assertEqual(
                saved["requested_changes"][0]["variable"],
                "MODE_IF.ALT_FRZ_REQ",
            )
            self.assertEqual(saved["requested_changes"][0]["status"], "requested")

    def test_change_history_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            status = RuntimeStatus(Path(directory) / "status.json", max_changes=2)
            for value in range(3):
                status.record_change("TEST", value)

            changes = status.snapshot()["requested_changes"]
            self.assertEqual([change["value"] for change in changes], [2, 1])


if __name__ == "__main__":
    unittest.main()
