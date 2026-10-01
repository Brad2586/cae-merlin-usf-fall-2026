"""Windows SAPI text-to-speech adapter for local simulator testing."""

from __future__ import annotations

import queue
import threading

import pythoncom
import win32com.client

from config.config import get_tts_mode


class WindowsTTS:
    """Speak asynchronously through an installed Windows SAPI voice."""

    def __init__(self, rate: int = 1):
        self.rate = rate
        self._queue: "queue.Queue[str | None]" = queue.Queue()
        self._worker = threading.Thread(
            target=self._run,
            name="WindowsSAPI",
            daemon=True,
        )
        self._worker.start()

    @staticmethod
    def _should_speak(priority: str) -> bool:
        mode = get_tts_mode()
        if priority == "bulk" and mode in ("minimal", "fast"):
            return False
        if priority == "minimal" and mode != "fast":
            return False
        if priority == "normal" and mode == "minimal":
            return False
        return True

    def say(self, message, priority="normal", **_kwargs) -> None:
        text = str(message).strip()
        if text and self._should_speak(priority):
            self._queue.put(text)

    def _run(self) -> None:
        pythoncom.CoInitialize()
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Rate = self.rate
            while True:
                text = self._queue.get()
                if text is None:
                    return
                try:
                    voice.Speak(text)
                except Exception as exc:
                    print(f"[WINDOWS_TTS_ERROR] {exc}")
        finally:
            pythoncom.CoUninitialize()

    def close(self) -> None:
        self._queue.put(None)
        self._worker.join(timeout=2.0)

