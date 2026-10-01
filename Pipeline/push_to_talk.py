"""Push-to-talk microphone input that does not require a wake-word model."""

from __future__ import annotations

import time
from collections import deque

import numpy as np

from audio_pipeline import AudioPipeline, FRAME_SIZE, SAMPLE_RATE
from logger import log


class PushToTalkPipeline(AudioPipeline):
    """Wait for Enter, then capture one utterance and transcribe it."""

    def __init__(
        self,
        device="cuda",
        whisper_name="small.en",
        compute_type=None,
        normalizer=None,
    ):
        super().__init__(
            wakeword_model=None,
            thresholds={},
            debounce_time=0,
            device=device,
            whisper_name=whisper_name,
            compute_type=compute_type,
            normalizer=normalizer,
        )

    def _record_one_utterance(self):
        pre_roll = deque(maxlen=10)
        frames = []
        silent_frames = 0
        required_silent_frames = 10
        speech_started = False

        print("Waiting for speech...")
        while True:
            frame = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
            is_speech = self.vad.is_speech(frame, SAMPLE_RATE)

            if not speech_started:
                pre_roll.append(frame)
                if not is_speech:
                    continue
                speech_started = True
                frames.extend(pre_roll)
                pre_roll.clear()
                log("[AUDIO]", "Push-to-talk recording started")
                print("Recording...")
                continue

            frames.append(frame)
            if is_speech:
                silent_frames = 0
            else:
                silent_frames += 1

            if silent_frames >= required_silent_frames:
                log("[AUDIO]", "Push-to-talk silence detected")
                print("Silence detected")
                break

        audio_int16 = np.frombuffer(b"".join(frames), dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0

    def listen_and_transcribe(self) -> str:
        input("\nPress Enter, then speak (Ctrl+C to stop): ")
        audio = self._record_one_utterance()

        start = time.time()
        transcription = self.transcribe(audio).strip().lower().rstrip(".")
        log("[TRANSCRIPTION_AFTER]", transcription, time.time() - start)
        return transcription

