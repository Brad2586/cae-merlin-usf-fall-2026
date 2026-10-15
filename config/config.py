# config.py
import json
from pathlib import Path

_config_file = Path(__file__).parent / "config.json"

# Defaults
_mode = "lenient"
_tts_mode = "normal"

# Initialize from the JSON file at import time
try:
    with open(_config_file, "r") as f:
        data = json.load(f)
        _mode = data.get("mode", _mode)
        if _mode not in ["strict", "lenient"]:
            _mode = "lenient"

        _tts_mode = data.get("tts_mode", _tts_mode)
        if _tts_mode not in ["minimal", "normal", "fast"]:
            raise ValueError(f"Invalid tts_mode in config: {_tts_mode}")

except FileNotFoundError:
    pass  # keep defaults
except json.JSONDecodeError:
    pass  # keep defaults


def load_config(path=None):
    """Reload config from file."""
    global _mode, _tts_mode
    config_path = path or _config_file
    with open(config_path, "r") as f:
        data = json.load(f)

    mode = data.get("mode", "lenient")
    if mode not in ["strict", "lenient"]:
        raise ValueError("Invalid mode in config")
    _mode = mode

    tts_mode = data.get("tts_mode", "normal")
    if tts_mode not in ["minimal", "normal", "fast"]:
        raise ValueError("Invalid tts_mode in config")
    _tts_mode = tts_mode


def get_mode():
    return _mode


def is_strict():
    return _mode == "strict"


def set_mode(new_mode):
    global _mode
    if new_mode not in ["strict", "lenient"]:
        raise ValueError("Invalid mode")
    _mode = new_mode


def get_tts_mode():
    return _tts_mode


def get_variable_ranges():
    """Return the variable_range block from config.json, or an empty dict if unavailable."""
    try:
        with open(_config_file, "r") as f:
            data = json.load(f)
        return data.get("variable_range", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_audio_settings():
    """Return voice-capture settings with safe defaults."""
    defaults = {
        "speech_start_timeout": 5.0,
        "end_silence_duration": 0.75,
        "pre_speech_buffer": 0.3,
        "whisper_beam_size": 3,
        "noise_reduction_enabled": True,
        "vad_aggressiveness": 2,
        "speech_confirmation_frames": 3,
        "minimum_command_duration": 0.25,
        "noise_gate_multiplier": 1.8,
        "highpass_cutoff_hz": 100,
    }
    try:
        with open(_config_file, "r") as f:
            data = json.load(f)
        configured = data.get("audio", {})
        if isinstance(configured, dict):
            defaults.update(
                {key: configured[key] for key in defaults if key in configured}
            )
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return defaults


def get_communication_settings():
    """Return automatic reconnect settings with safe defaults."""
    defaults = {
        "auto_reconnect": True,
        "reconnect_initial_delay": 1.0,
        "reconnect_max_delay": 15.0,
        "reconnect_backoff": 2.0,
        "reconnect_max_attempts": 0,
        "keep_alive_interval": 5.0,
    }
    try:
        with open(_config_file, "r") as f:
            data = json.load(f)
        configured = data.get("communication", {})
        if isinstance(configured, dict):
            defaults.update(
                {key: configured[key] for key in defaults if key in configured}
            )
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return defaults