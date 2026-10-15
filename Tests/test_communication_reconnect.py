import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Pipeline"))

from Pipeline.communication_client import CommunicationClient


class CommunicationReconnectTests(unittest.TestCase):
    def test_reconnect_retries_and_restores_session(self):
        client = CommunicationClient(
            auto_reconnect=True,
            reconnect_initial_delay=0.1,
            reconnect_max_delay=0.1,
            reconnect_max_attempts=3,
        )
        attempts = []
        restored = []

        def connect_once():
            attempts.append(True)
            if len(attempts) == 2:
                client._connected.set()
                return True
            return False

        client._connect_once = connect_once
        client._restore_host_session = lambda: restored.append(True)

        client._reconnect_loop()

        self.assertEqual(len(attempts), 2)
        self.assertEqual(restored, [True])
        self.assertTrue(client._connected.is_set())

    def test_session_restore_updates_existing_host_dictionary(self):
        client = CommunicationClient()
        original_host_dict = {
            "OLD": {"index": 99, "type": 3, "value": b"\x00\x00\x00\x00"}
        }
        client._host_dict_ref = original_host_dict
        client._update_page_variables = [{"name": "NEW", "type_code": 3}]
        restored = {
            "NEW": {"index": 2, "type": 3, "value": b"\x01\x00\x00\x00"}
        }
        client.create_update_page = lambda *args, **kwargs: restored
        keep_alive = []
        client.set_keep_alive_variables = (
            lambda variables, list_type=0: keep_alive.extend(variables)
        )

        client._restore_host_session()

        self.assertEqual(original_host_dict, restored)
        self.assertEqual(keep_alive[0]["name"], "NEW")
        self.assertEqual(keep_alive[0]["index"], 2)


if __name__ == "__main__":
    unittest.main()
