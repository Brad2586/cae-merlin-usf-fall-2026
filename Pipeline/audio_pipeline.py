from collections import deque
import math
import numpy as np
import pyaudio
import webrtcvad
import time
from scipy.signal import butter, sosfilt
from logger import log

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

class AudioPipeline:
    def __init__(
        self,
        wakeword_model,
        thresholds,
        debounce_time,
        whisper_processor=None,          # old implemenation
        whisper_model=None,              # old implementation
        device="cuda",
        whisper_name=None, # path to whisper model on local storage or model name (i.e. small.en)
        compute_type=None,                # override compute (i.e. int8)
        normalizer=None,
        speech_start_timeout=5.0,
        end_silence_duration=0.75,
        pre_speech_buffer=0.3,
        whisper_beam_size=3,
        noise_reduction_enabled=True,
        vad_aggressiveness=2,
        speech_confirmation_frames=3,
        minimum_command_duration=0.25,
        noise_gate_multiplier=1.8,
        highpass_cutoff_hz=100,
    ):
        self.wakeword_model = wakeword_model
        self.thresholds = thresholds
        self.debounce_time = debounce_time
        self.device = device
        self.normalizer = normalizer
        self.speech_start_timeout = max(float(speech_start_timeout), 0.5)
        self.end_silence_duration = max(float(end_silence_duration), 0.3)
        self.pre_speech_buffer = max(float(pre_speech_buffer), 0.0)
        self.whisper_beam_size = max(int(whisper_beam_size), 1)
        self.noise_reduction_enabled = bool(noise_reduction_enabled)
        self.speech_confirmation_frames = max(int(speech_confirmation_frames), 1)
        self.minimum_command_duration = max(float(minimum_command_duration), 0.0)
        self.noise_gate_multiplier = max(float(noise_gate_multiplier), 1.0)
        self.highpass_cutoff_hz = min(max(float(highpass_cutoff_hz), 0.0), 3000.0)
        self.ambient_rms = 0.0
        self._ambient_samples = 0

        # faster whisper initialization
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "run pip install faster-whisper. It is not installed."
            ) from e

        # Use provided path/id; if not provided, fall back to what you previously used

        if whisper_name is None:
            raise ValueError(
                "you must create a path to whisper model on local storage or give the model size ID "
                " examples: paths['WHISPER_PATH'] or 'small.en'."
            )

        if compute_type is None:
            compute_type = "float16" if device.startswith("cuda") else "int8" # default compute

        self.fw = WhisperModel(
            whisper_name,
            device="cuda" if device.startswith("cuda") else "cpu",
            compute_type=compute_type,
        )

        # init unchanged here
        vad_level = min(max(int(vad_aggressiveness), 0), 3)
        self.vad = webrtcvad.Vad(vad_level)
        
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SIZE,
        )

    @staticmethod
    def _frame_rms(frame):
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples * samples)))

    def _update_ambient_noise(self, frame):
        """Track a conservative ambient level using non-speech frames."""
        rms = self._frame_rms(frame)
        if self._ambient_samples == 0:
            self.ambient_rms = rms
        else:
            # Slow adaptation prevents a single noise burst from raising the
            # gate enough to hide the user's next command.
            self.ambient_rms = (0.98 * self.ambient_rms) + (0.02 * rms)
        self._ambient_samples += 1

    def _is_command_speech(self, frame):
        if not self.vad.is_speech(frame, SAMPLE_RATE):
            return False
        if not self.noise_reduction_enabled or self._ambient_samples == 0:
            return True
        return self._frame_rms(frame) >= self.ambient_rms * self.noise_gate_multiplier

    def _reduce_noise(self, audio):
        """Remove low-frequency rumble and attenuate audio below the noise floor."""
        if not self.noise_reduction_enabled or audio.size == 0:
            return audio

        filtered = audio
        if self.highpass_cutoff_hz > 0:
            sos = butter(
                2,
                self.highpass_cutoff_hz / (SAMPLE_RATE / 2),
                btype="highpass",
                output="sos",
            )
            filtered = sosfilt(sos, filtered).astype(np.float32)

        if self._ambient_samples > 0:
            gate = (
                self.ambient_rms / np.iinfo(np.int16).max
            ) * self.noise_gate_multiplier
            gated = filtered.copy()
            frame_samples = FRAME_SIZE
            for start in range(0, gated.size, frame_samples):
                end = min(start + frame_samples, gated.size)
                section = gated[start:end]
                rms = float(np.sqrt(np.mean(section * section))) if section.size else 0
                if rms < gate:
                    gated[start:end] *= 0.15
            filtered = gated

        return filtered

    # old implementation copied buffer numpy array on every iteration of listening.
    # numpy arrays expand length by addding length of old data + new
    # this means, on every iteration, copying is done
    # new implementation uses bytearray, which has faster appending and only converts to numpy array at 80ms
    def listen_for_wake_word(self):
        # collect data until we have 80ms chunks 
        # 1280 audio samples at 16kHz is 2560 byte chunks (int6)
        leftover = bytearray()
        chunk_bytes = 2560

        print("Listening for wake word...")
        while True:
            frame_bytes = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
            if not self.vad.is_speech(frame_bytes, SAMPLE_RATE):
                self._update_ambient_noise(frame_bytes)
            leftover.extend(frame_bytes)

            while len(leftover) >= chunk_bytes:
                chunk = bytes(leftover[:chunk_bytes])
                del leftover[:chunk_bytes]

                pcm = np.frombuffer(chunk, dtype=np.int16)

                # Use the openWakeWord API's predict method with threshold-based
                # debouncing implemented externally. The installed openwakeword
                # package version exposes `debounce_time` only on
                # `predict_clip`, not on `predict`, so we keep the streaming
                # loop simple and handle debouncing ourselves via
                # `self.wakeword_model.reset()` and silence gating.
                prediction = self.wakeword_model.predict(
                    pcm,
                    threshold=self.thresholds,
                )

                # Apply the same external threshold check used in
                # Tests/transcriptionTest.py.
                if any(prediction[k] > self.thresholds[k] for k in self.thresholds):
                    self.wakeword_model.reset()
                    log("[AUDIO]", "Wake word detected")
                    print("Wake word detected. Ready for command...")
                    # Frames are read in 30 ms blocks but wake-word inference uses
                    # 80 ms chunks. Preserve any unread remainder so the beginning
                    # of a command spoken immediately after "Merlin" is not lost.
                    return bytes(leftover)

    def record_until_silence(self, initial_audio=b""):
        """Wait for a command, then record until the speaker finishes.

        Silence before the first spoken command does not end recording. This
        gives the user time to pause after saying the wake word.
        """
        frames = []
        pre_roll = deque(
            maxlen=max(1, math.ceil(self.pre_speech_buffer * 1000 / FRAME_DURATION_MS))
        )
        speech_started = False
        silent_frames = 0
        waiting_frames = 0
        candidate_speech_frames = 0
        recorded_speech_frames = 0
        required_silent_frames = math.ceil(
            self.end_silence_duration * 1000 / FRAME_DURATION_MS
        )
        max_waiting_frames = math.ceil(
            self.speech_start_timeout * 1000 / FRAME_DURATION_MS
        )

        log("[AUDIO]", "Waiting for command speech")
        print(f"Listening for command (up to {self.speech_start_timeout:g} seconds)...")
        while True:
            frame = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
            is_speech = self._is_command_speech(frame)

            if not speech_started:
                pre_roll.append(frame)
                waiting_frames += 1
                if is_speech:
                    candidate_speech_frames += 1
                    if candidate_speech_frames >= self.speech_confirmation_frames:
                        speech_started = True
                        recorded_speech_frames = candidate_speech_frames
                        if initial_audio:
                            frames.append(initial_audio)
                        frames.extend(pre_roll)
                        log("[AUDIO]", "Command speech detected")
                        print("Command detected...")
                else:
                    candidate_speech_frames = 0
                    self._update_ambient_noise(frame)
                if not speech_started and waiting_frames >= max_waiting_frames:
                    log("[AUDIO]", "No command detected before timeout")
                    print("No command heard. Returning to wake-word listening.")
                    return np.array([], dtype=np.float32)
                continue

            frames.append(frame)
            if is_speech:
                recorded_speech_frames += 1
            silent_frames = 0 if is_speech else silent_frames + 1
            if silent_frames >= required_silent_frames:
                log("[AUDIO]", "Silence detected")
                print("Command recording complete.")
                break

        minimum_speech_frames = math.ceil(
            self.minimum_command_duration * 1000 / FRAME_DURATION_MS
        )
        if recorded_speech_frames < minimum_speech_frames:
            log("[AUDIO]", "Rejected command shorter than minimum duration")
            print("Ignored a short noise event. Returning to wake-word listening.")
            return np.array([], dtype=np.float32)

        audio_int16 = np.frombuffer(b"".join(frames), dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0
        
    def transcribe(self, audio):
        # audio taken in as flat32 numpy array at 16kHz 
        # newer faster whisper transcription used here
        if audio.size == 0:
            return ""
        audio = self._reduce_noise(audio)
        audio = audio - np.mean(audio)
            
            # Normalize amplitude to a safe peak level
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio * (0.95 / peak)
        segments, _info = self.fw.transcribe(
            audio,
            language="en",
            beam_size=self.whisper_beam_size,
            condition_on_previous_text=False,
            vad_filter=True)
        text = "".join(seg.text for seg in segments)
        log("[TRANSCRIPTION_BEFORE]", text)
        text = self.normalizer.normalize(text)

        return text # final result is still str just like old implementation


    def listen_and_transcribe(self):
        initial_audio = self.listen_for_wake_word()
        
        audio = self.record_until_silence(initial_audio=initial_audio)

        start = time.time()
        transcription = self.transcribe(audio).strip().lower().rstrip('.')        
        transcribe_time = time.time() - start
        log("[TRANSCRIPTION_AFTER]", transcription, transcribe_time)
        return transcription

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
