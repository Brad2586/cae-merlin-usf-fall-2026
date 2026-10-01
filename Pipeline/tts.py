import os
import threading
import queue
import time
from typing import Optional, Callable
import scipy.signal

import numpy as np
import sounddevice as sd
from piper import PiperVoice
from config.config import get_tts_mode

class PiperTTS:
    def __init__(
        self,
        voice_model_path,
        rate: float = 1.15,
        on_done: Optional[Callable[[str], None]] = None
    ):
        if not os.path.exists(voice_model_path):
            raise RuntimeError(f"Piper voice model not found: {voice_model_path}")

        self.rate = rate
        self._on_done = on_done
        self.voice = PiperVoice.load(voice_model_path)
        self._q: "queue.Queue[str]" = queue.Queue()
        self._stop_evt = threading.Event()
        self._speaking_evt = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._interrupt_evt = threading.Event()
        self._worker.start()

    @property
    def _tts_mode(self):
        return get_tts_mode()

    # ---------------------------------------------------
    # Public API
    # ---------------------------------------------------

    def say(self, text: str, wait: bool = False, priority: str = "normal"):
        text = text.strip()
        if not text:
            return

        mode = self._tts_mode
        # Gate based on priority vs mode
        if priority == "bulk" and mode in ("minimal", "fast"):
            return
        elif priority == "minimal" and mode != "fast":  # suppress in normal and minimal, speak in fast
            return
        elif priority == "normal" and mode == "minimal":
            return
        # "critical" always passes through

        done_evt = threading.Event() if wait else None
        self._q.put((text, done_evt))

        if wait and done_evt:
            done_evt.wait()

    def speak_now(self, text: str):
        self.interrupt()
        self.clear_queue()
        self.say(text)

    def interrupt(self):
        self._interrupt_evt.set()

    def clear_queue(self):
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def wait_until_done(self):
        while self._speaking_evt.is_set():
            time.sleep(0.01)

    def is_speaking(self) -> bool:
        return self._speaking_evt.is_set()

    def close(self):
        self._stop_evt.set()
        self.clear_queue()

    # ---------------------------------------------------
    # Worker
    # ---------------------------------------------------

    def _run(self):
        while not self._stop_evt.is_set():
            try:
                text, done_evt = self._q.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._speaking_evt.set()
                self._speak(text)
            finally:
                self._speaking_evt.clear()
                self._interrupt_evt.clear()

                if self._on_done:
                    try:
                        self._on_done(text)
                    except Exception:
                        pass

                if done_evt:
                    done_evt.set()

    # ---------------------------------------------------
    # Fast in-memory speech
    # ---------------------------------------------------
    def _speak(self, text: str):
        audio_gen = self.voice.synthesize(text)

        raw_bytes = b""
        sample_rate = None
        sample_width = None
        num_channels = None

        for chunk in audio_gen:
            raw_bytes += chunk.audio_int16_bytes
            sample_rate = chunk.sample_rate
            sample_width = chunk.sample_width
            num_channels = chunk.sample_channels

        if not raw_bytes:
            return

        # Convert raw PCM bytes to numpy array
        audio_array = np.frombuffer(raw_bytes, dtype=np.int16)

        # For multi-channel audio, reshape
        if num_channels and num_channels > 1:
            audio_array = audio_array.reshape(-1, num_channels)

        # Apply rate by resampling
        if self.rate != 1.0:
            num_samples = int(len(audio_array) / self.rate)
            if num_channels and num_channels > 1:
                # Resample each channel separately
                resampled = [
                    scipy.signal.resample(audio_array[:, ch], num_samples)
                    for ch in range(num_channels)
                ]
                audio_array = np.stack(resampled, axis=-1)
            else:
                audio_array = scipy.signal.resample(audio_array, num_samples)

            # Convert back to int16
            audio_array = np.round(audio_array).astype(np.int16)

        # Normalize to float32 for sounddevice
        samples = audio_array.astype(np.float32) / np.iinfo(np.int16).max

        # Play audio
        sd.play(samples, samplerate=sample_rate)

        # Wait for playback or interruption
        while sd.get_stream().active:
            if self._interrupt_evt.is_set():
                sd.stop()
                break
            time.sleep(0.01)
    