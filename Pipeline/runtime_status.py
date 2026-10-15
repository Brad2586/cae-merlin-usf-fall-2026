"""Small file-backed status store consumed by the companion dashboard."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATUS_PATH = PROJECT_ROOT / "Logs" / "runtime_status.json"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class RuntimeStatus:
    def __init__(self, path: str | Path = DEFAULT_STATUS_PATH, max_changes: int = 100):
        self.path = Path(path)
        self.max_changes = max(int(max_changes), 1)
        self._lock = threading.RLock()
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None
        self._data: dict[str, Any] = {
            "merlin_state": "offline",
            "server_state": "disconnected",
            "server_endpoint": "127.0.0.1:10013",
            "active_model": "unknown",
            "last_transcription": "",
            "last_command": "",
            "message": "",
            "updated_at": _now(),
            "requested_changes": [],
        }

    def reset_session(self, **values: Any) -> None:
        with self._lock:
            self._data.update(
                {
                    "merlin_state": "starting",
                    "server_state": "disconnected",
                    "last_transcription": "",
                    "last_command": "",
                    "message": "",
                    "requested_changes": [],
                }
            )
            self._data.update(values)
            self._write()

    def update(self, **values: Any) -> None:
        with self._lock:
            self._data.update(values)
            self._write()

    def record_command(self, transcription: str, command_source: str) -> None:
        with self._lock:
            self._data["last_transcription"] = transcription
            self._data["last_command"] = command_source
            self._write()

    def record_change(
        self,
        variable: str,
        value: Any,
        *,
        display_name: str | None = None,
        status: str = "requested",
    ) -> None:
        with self._lock:
            entry = {
                "time": _now(),
                "variable": variable,
                "display_name": display_name or variable,
                "value": value,
                "status": status,
            }
            changes = self._data.setdefault("requested_changes", [])
            changes.insert(0, entry)
            del changes[self.max_changes :]
            self._write()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def start_heartbeat(self, interval: float = 2.0) -> None:
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()

        def heartbeat():
            while not self._heartbeat_stop.wait(max(float(interval), 0.5)):
                try:
                    with self._lock:
                        self._write()
                except OSError:
                    pass

        self._heartbeat_thread = threading.Thread(
            target=heartbeat,
            name="RuntimeStatusHeartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()

    def _write(self) -> None:
        self._data["updated_at"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._data, indent=2, ensure_ascii=False) + "\n"
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(
                file_descriptor, "w", encoding="utf-8", newline="\n"
            ) as file:
                file.write(payload)
            os.replace(temporary_name, self.path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise


runtime_status = RuntimeStatus()
