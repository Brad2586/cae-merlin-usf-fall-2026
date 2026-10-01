
import os
import sys
import warnings 


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import numpy as np
import pyaudio
import webrtcvad
import time
import torch
from pathlib import Path
from openwakeword.model import Model

from config.load_paths import load_paths


paths = load_paths()

# ---------------- Settings ----------------
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
THRESHOLDS = {"default": 0.5}
DEBOUNCE_TIME = 1.0
WHISPER_MODEL_NAME = "small.en"
OUTPUT_FILE = Path("transcriptions.txt")
OUTPUT_FILE.touch(exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"

THRESHOLDS = {
    "merlin": 0.5,
    "merlin2": 0.5,
    "hey_merlin": 0.5,
}

DEBOUNCE_TIME = 0.25

# ---------------- Initialize Models ----------------
# Wake word

oww = Model(
    wakeword_models=paths["MODEL_PATHS"],
    inference_framework="tflite"
)

# Faster Whisper
try:
    from faster_whisper import WhisperModel
except ImportError:
    raise ImportError("Install faster-whisper with `pip install faster-whisper`")

fw = WhisperModel(
    WHISPER_MODEL_NAME,
    device=device,
    compute_type="float16" if device == "cuda" else "int8"
)

# VAD & audio
vad = webrtcvad.Vad(3)
audio_interface = pyaudio.PyAudio()
stream = audio_interface.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=SAMPLE_RATE,
    input=True,
    frames_per_buffer=FRAME_SIZE
)

# ---------------- Helper Functions ----------------
def listen_for_wake_word():
    leftover = bytearray()
    chunk_bytes = 2560
    print("Listening for wake word...")
    while True:
        frame_bytes = stream.read(FRAME_SIZE, exception_on_overflow=False)
        leftover.extend(frame_bytes)
        while len(leftover) >= chunk_bytes:
            chunk = bytes(leftover[:chunk_bytes])
            del leftover[:chunk_bytes]
            pcm = np.frombuffer(chunk, dtype=np.int16)
            prediction = oww.predict(pcm, threshold=THRESHOLDS, debounce_time=DEBOUNCE_TIME)
            if any(prediction[k] > THRESHOLDS[k] for k in THRESHOLDS):
                oww.reset()
                print("Wake word detected")
                return

def record_until_silence():
    frames = []
    silent_frames = 0
    required_silent_frames = 14
    print("Recording...")
    while True:
        frame = stream.read(FRAME_SIZE, exception_on_overflow=False)
        frames.append(frame)
        if vad.is_speech(frame, SAMPLE_RATE):
            silent_frames = 0
        else:
            silent_frames += 1
        if silent_frames >= required_silent_frames:
            print("Silence detected")
            break
    audio_int16 = np.frombuffer(b"".join(frames), dtype=np.int16)
    return audio_int16.astype(np.float32) / 32768.0

def transcribe_audio(audio):
    segments, _info = fw.transcribe(audio, language="en", beam_size=1, vad_filter=False)
    text = "".join(seg.text for seg in segments)
    return text.strip().lower()

# ---------------- Main Loop ----------------
try:
    while True:
        listen_for_wake_word()
        audio = record_until_silence()
        start = time.time()
        transcription = transcribe_audio(audio)
        transcribe_time = time.time() - start
        print("Transcription:", transcription)
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(transcription + "\n")
except KeyboardInterrupt:
    print("Exiting...")
finally:
    stream.stop_stream()
    stream.close()
    audio_interface.terminate()