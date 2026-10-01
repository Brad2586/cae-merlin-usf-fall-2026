from email.mime import audio

import numpy as np
import pyaudio
import webrtcvad
import time
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
        normalizer=None
    ):
        self.wakeword_model = wakeword_model
        self.thresholds = thresholds
        self.debounce_time = debounce_time
        self.device = device
        self.normalizer = normalizer

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
        self.vad = webrtcvad.Vad(2) # 0-3, higher is more aggressive about filtering out non-speech
        
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SIZE,
        )

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
                    print("Wake word detected")
                    return

    def record_until_silence(self):
        frames = []
        silent_frames = 0
        required_silent_frames = 10
        log("[AUDIO]", "Recording Started")
        print("Recording...") #remove later
        while True:
            frame = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
            frames.append(frame)

            if self.vad.is_speech(frame, SAMPLE_RATE):
                silent_frames = 0
            
            else:
                silent_frames += 1

            if silent_frames >= required_silent_frames:
                log("[AUDIO]", "Silence detected")
                print("Silence detected") #remove later
                break

        audio_int16 = np.frombuffer(b"".join(frames), dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0
        
    def transcribe(self, audio):
        # audio taken in as flat32 numpy array at 16kHz 
        # newer faster whisper transcription used here
        audio = audio - np.mean(audio)
            
            # Normalize amplitude to a safe peak level
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio * (0.95 / peak)
        segments, _info = self.fw.transcribe(
            audio,
            language="en",
            beam_size=1,      # can be changed for accuracy at the cost of small speed change. recommended for our implementation if beam_size=1 is too inaccurate is 2.
            vad_filter=True ) # doesnt hurt (might help a little)
        text = "".join(seg.text for seg in segments)
        log("[TRANSCRIPTION_BEFORE]", text)
        text = self.normalizer.normalize(text)

        return text # final result is still str just like old implementation


    def listen_and_transcribe(self):
        self.listen_for_wake_word()
        
        audio = self.record_until_silence()

        start = time.time()
        transcription = self.transcribe(audio).strip().lower().rstrip('.')        
        transcribe_time = time.time() - start
        log("[TRANSCRIPTION_AFTER]", transcription, transcribe_time)
        return transcription

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
