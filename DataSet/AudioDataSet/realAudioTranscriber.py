import os
import time
import wave
from pathlib import Path

import numpy as np
import scipy.signal
from faster_whisper import WhisperModel


# -----------------------------
# CONFIG
# -----------------------------
WAV_ROOT = "./DataSet/AudioDataset/input_wavs"          # folder with .wav files
OUTPUT_TXT = "./DataSet/AudioDataset/transcriptions.txt"


# -----------------------------
# WAV loader
# -----------------------------
def load_wav_as_float32(wav_path: Path) -> np.ndarray:
    with wave.open(str(wav_path), "rb") as wf:
        n_channels  = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames    = wf.getnframes()
        raw         = wf.readframes(n_frames)

    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    target_sr = 16000
    if sample_rate != target_sr:
        num_samples = int(len(audio) * target_sr / sample_rate)
        audio = scipy.signal.resample(audio, num_samples).astype(np.float32)

    return audio


# -----------------------------
# Transcription
# -----------------------------
def transcribe(model: WhisperModel, audio: np.ndarray) -> str:
    segments, _ = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        vad_filter=False,
    )
    return "".join(seg.text for seg in segments).strip()


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    import torch

    device       = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    model = WhisperModel(
        "small.en",
        device=device,
        compute_type=compute_type,
    )

    wav_files = sorted(Path(WAV_ROOT).rglob("*.wav"))

    if not wav_files:
        print(f"No .wav files found in {WAV_ROOT}")
        exit(0)

    os.makedirs(Path(OUTPUT_TXT).parent, exist_ok=True)

    total_time = 0

    with open(OUTPUT_TXT, "w", encoding="utf-8") as out:
        for i, wav_path in enumerate(wav_files):
            start = time.time()

            audio = load_wav_as_float32(wav_path)
            text  = transcribe(model, audio)

            elapsed = time.time() - start
            total_time += elapsed

            print(f"[{i+1}/{len(wav_files)}] {wav_path.name} ({elapsed:.2f}s)")
            print(f"   → {text}")

            out.write(f"{wav_path.name}:\n")
            out.write(f"{text}\n\n")

    print("\nDone.")
    print(f"Processed {len(wav_files)} files")
    print(f"Total time: {total_time:.2f}s")
    print(f"Saved to: {OUTPUT_TXT}")