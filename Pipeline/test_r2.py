
from parse_llm_output import LLMOutputParser


class FakeCommunicationClient:
    def __init__(self, current_value):
        self.current_value = current_value

    def request_update(self, list_type, variables):
        return {
            variables[0]["name"]: {
                "value": self.current_value
            }
        }


def test_check_host_value():
    host_dict = {
        "TEST_VARIABLE": {
            "list_type": 0,
            "index": 1,
            "type": 3,
            "num_dims": 0,
            "dimensions": []
        }
    }

    client = FakeCommunicationClient(
        current_value=(5).to_bytes(
            4, "little", signed=True
        )
    )

    parser = LLMOutputParser(
        communication_client=client,
        host_dict=host_dict,
        llm=None,
        audio_pipeline=None,
        tts=None,
        exit_handler=None
    )

    same = parser.check_host_value(
        "TEST_VARIABLE",
        (5).to_bytes(4, "little", signed=True)
    )

    different = parser.check_host_value(
        "TEST_VARIABLE",
        (10).to_bytes(4, "little", signed=True)
    )

    assert same == "same", f"Expected same, got {same}"
    assert different == "different", f"Expected different, got {different}"

    print("R2 comparison tests passed!")



def test_set_variable_if_changed():
    class RecordingClient:
        def __init__(self, current_value):
            self.current_value = current_value
            self.set_calls = []

        def request_update(self, list_type, variables):
            if self.current_value is None:
                return {}
            return {
                variables[0]["name"]: {
                    "value": self.current_value
                }
            }

        def set_variable(self, list_type, var_index, value, dimensions=None):
            self.set_calls.append((list_type, var_index, value, dimensions))

    host_dict = {
        "TEST_VARIABLE": {
            "list_type": 0,
            "index": 1,
            "type": 3,
            "num_dims": 0,
            "dimensions": []
        }
    }

    five = (5).to_bytes(4, "little", signed=True)
    ten = (10).to_bytes(4, "little", signed=True)

    client = RecordingClient(five)

    parser = LLMOutputParser(
        communication_client=client,
        host_dict=host_dict,
        llm=None,
        audio_pipeline=None,
        tts=None,
        exit_handler=None
    )

    # Test 1: Same value should not send SET
    assert parser.set_variable_if_changed("TEST_VARIABLE", five) == "skipped"
    assert len(client.set_calls) == 0

    # Test 2: Different value should send one SET
    assert parser.set_variable_if_changed("TEST_VARIABLE", ten) == "sent"
    assert len(client.set_calls) == 1

    # Test 3: Missing host value should not send another SET
    client.current_value = None
    assert parser.set_variable_if_changed("TEST_VARIABLE", ten) == "failed"
    assert len(client.set_calls) == 1

    print("R2 SET decision tests passed!")

def test_flameout_array_layout():
    values = b"\x00\x01\x00\x00"

    assert len(values) == 4
    assert values[0] == 0
    assert values[1] == 1
    assert values[2] == 0
    assert values[3] == 0

    print("R2 array byte-layout test passed!")


def test_array_comparison():
    class ArrayClient:
        def request_update(self, list_type, variables):
            return {
                "MALF.FLAME_OUT": {
                    "value": b"\x00\x01\x00\x00"
                }
            }

    parser = LLMOutputParser(
        communication_client=ArrayClient(),
        host_dict={
            "MALF.FLAME_OUT": {
                "list_type": 0,
                "index": 0,
                "type": 1,
                "num_dims": 1,
                "dimensions": [4]
            }
        },
        llm=None,
        audio_pipeline=None,
        tts=None,
        exit_handler=None
    )

    assert parser.check_host_value(
        "MALF.FLAME_OUT", b"\x01", dimensions=[1]
    ) == "same"

    assert parser.check_host_value(
        "MALF.FLAME_OUT", b"\x01", dimensions=[0]
    ) == "different"

    assert parser.check_host_value(
        "MALF.FLAME_OUT", b"\x01", dimensions=[4]
    ) == "unknown"

    print("R2 array comparison tests passed!")


def test_set_acknowledgment():
    import socket
    import struct
    from communication_client import CommunicationClient

    class FakeSocket:
        def __init__(self, response):
            self.response = response
            self.sent = []
            self.timeout = None
            self.closed = False

        def sendall(self, data):
            self.sent.append(data)

        def recv(self, n):
            if not self.response:
                return b""
            data = self.response[:n]
            self.response = self.response[n:]
            return data

        def gettimeout(self):
            return self.timeout

        def settimeout(self, timeout):
            self.timeout = timeout

        def close(self):
            self.closed = True

    # Test 1: Host sends a valid, zero-length acknowledgment.
    client = CommunicationClient()
    client.sock = FakeSocket(b"\x4b\x00\x00\x00" + struct.pack("<I", 0))

    client.set_variable(0, 1, struct.pack("<i", 5))

    assert len(client.sock.sent) == 1
    assert client.sock.sent[0][0] == 0x53
    assert not client.sock.closed
    assert client.sock.timeout is None

    # Test 2: Host closes without sending an acknowledgment.
    client2 = CommunicationClient()
    client2.sock = FakeSocket(b"")

    try:
        client2.set_variable(0, 1, struct.pack("<i", 5))
        raise AssertionError("Expected ConnectionError")
    except ConnectionError:
        pass

    assert client2.sock.closed
    assert client2.running is False

    print("R2 SET acknowledgment tests passed!")

def test_fire_sets_flameout_and_malfunction_sets_toggle():
    class RecordingClient:
        def __init__(self):
            self.calls = []

        def set_variable(self, list_type, var_index, value, dimensions=None):
            self.calls.append({
                "list_type": list_type,
                "index": var_index,
                "value": value,
                "dimensions": dimensions,
            })

    class SilentTTS:
        def say(self, message, priority="normal"):
            pass

    client = RecordingClient()
    parser = LLMOutputParser(
        communication_client=client,
        host_dict={
            "MALF.FLAME_OUT": {
                "list_type": 0,
                "index": 4,
                "type": 1,
                "num_dims": 1,
                "dimensions": [4],
                "common_name": "Engine Flameout Malfunction",
            },
            "MALF_IF.TOGGLE_REQ": {
                "list_type": 0,
                "index": 5,
                "type": 3,
                "num_dims": 0,
                "dimensions": [],
                "common_name": "Malfunction Toggle Request",
            },
        },
        llm=None,
        audio_pipeline=None,
        tts=SilentTTS(),
        exit_handler=None,
        mappings=[
            {
                "alias": "ENGINE_1_FLAME",
                "action": "enable",
                "variable": "MALF.FLAME_OUT",
                "value": 1,
                "index": 0,
                "time": None,
            },
            {
                "alias": "ENGINE_1_MALF",
                "action": "enable",
                "variable": "MALF_IF.TOGGLE_REQ",
                "value": 331,
                "index": None,
                "time": None,
            },
        ],
    )

    assert parser.set_llm_variable(
        "MALF.FLAME_OUT", True, alias_name="ENGINE_1_FLAME"
    )
    assert parser.set_llm_variable(
        "MALF_IF.TOGGLE_REQ", True, alias_name="ENGINE_1_MALF"
    )
    assert client.calls[0]["value"] == b"\x01"
    assert client.calls[0]["dimensions"] == [0]
    assert client.calls[0]["index"] == 4
    assert client.calls[1]["value"] == (331).to_bytes(4, "little", signed=True)
    assert client.calls[1]["dimensions"] == []
    print("Fire versus malfunction routing test passed!")


if __name__ == "__main__":
    test_check_host_value()
    test_set_variable_if_changed()
    test_flameout_array_layout()
    test_array_comparison()
    test_set_acknowledgment()
    test_fire_sets_flameout_and_malfunction_sets_toggle()
