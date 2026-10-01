import os
import sys
import json
import threading
import queue
import time
import wave
from pathlib import Path

import numpy as np
import scipy.signal
from piper import PiperVoice

# ---------------------------------------------------
# Path setup
# ---------------------------------------------------
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.load_paths import load_paths

paths = load_paths()

# ---------------------------------------------------
# TTS Class
# ---------------------------------------------------
class PiperTTS:
    def __init__(self, voice_model_path, output_dir="wav_outputs", rate=1.15):
        if not os.path.exists(voice_model_path):
            raise RuntimeError(f"Piper voice model not found: {voice_model_path}")

        self.voice = PiperVoice.load(voice_model_path)
        self.output_dir = output_dir
        self.rate = rate

        os.makedirs(self.output_dir, exist_ok=True)

        self._q = queue.Queue()
        self._stop_evt = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    # ---------------------------------------------------
    # Public API
    # ---------------------------------------------------
    def process_jsonl(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line {i}")
                    continue

                self._q.put((data, i))

    def wait_until_done(self):
        while not self._q.empty():
            time.sleep(0.1)

    def close(self):
        self._stop_evt.set()

    # ---------------------------------------------------
    # Worker
    # ---------------------------------------------------
    def _run(self):
        while not self._stop_evt.is_set():
            try:
                data, idx = self._q.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._process_entry(data, idx)
            finally:
                self._q.task_done()

    # ---------------------------------------------------
    # Core logic
    # ---------------------------------------------------
    def _process_entry(self, data: dict, idx: int):
        text = data.get("input", "").strip()
        output = data.get("output", {})

        if not text or not output:
            return

        tts_type = output.get("Type", "unknown")
        base_path = Path(self.output_dir) / tts_type

        if tts_type == "command":
            keys = output.get("parameters_keys", [])
            values = output.get("parameters_values", [])

            keys_str = "+".join(keys) if keys else "no_keys"
            values_str = "+".join(values) if values else "no_values"

            # sanitize keys and values
            keys_str = self.safe_filename(keys_str)
            values_str = self.safe_filename(values_str)

            base_path = base_path / keys_str / values_str

        elif tts_type in ("clarification", "error"):
            message = output.get("message", "no_message")
            safe_msg = self.safe_filename(message)
            base_path = base_path / safe_msg

        # ensure folder exists
        base_path.mkdir(parents=True, exist_ok=True)

        # filename
        filename = f"sample_{idx}"
        wav_path = base_path / f"{filename}.wav"
        json_path = base_path / f"{filename}.json"

        # --- Generate audio ---
        self._synthesize_to_wav(text, wav_path)

        # --- Save JSON ---
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved: {wav_path}")
        print(f"Saved: {json_path}")

    # ---------------------------------------------------
    # TTS → WAV  
    # ---------------------------------------------------
    def _synthesize_to_wav(self, text: str, output_path: Path):
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

        audio_array = np.frombuffer(raw_bytes, dtype=np.int16)

        if num_channels and num_channels > 1:
            audio_array = audio_array.reshape(-1, num_channels)

        # Apply speed change
        if self.rate != 1.0:
            num_samples = int(len(audio_array) / self.rate)

            if num_channels and num_channels > 1:
                resampled = [
                    scipy.signal.resample(audio_array[:, ch], num_samples)
                    for ch in range(num_channels)
                ]
                audio_array = np.stack(resampled, axis=-1)
            else:
                audio_array = scipy.signal.resample(audio_array, num_samples)

            audio_array = np.round(audio_array).astype(np.int16)

        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(num_channels or 1)
            wf.setsampwidth(sample_width or 2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_array.tobytes())

        print(f"Saved: {output_path}")

    # ---------------------------------------------------
    # Utility: sanitize filenames for Windows
    # ---------------------------------------------------
    @staticmethod
    def safe_filename(name: str, max_length: int = 50) -> str:
        import re
        # Replace illegal characters with underscores
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Trim to max_length
        return name[:max_length]


# ---------------------------------------------------
# Main
# ---------------------------------------------------
if __name__ == "__main__":
    voice_model_path = paths["TTS_VOICE_PATH"]

    INPUT_FILE = "./DataSet/AudioDataSet/audioDataSet.jsonl"   # your file
    OUTPUT_FOLDER = "./DataSet/AudioDataSet/wav_outputs"

    tts = PiperTTS(voice_model_path, output_dir=OUTPUT_FOLDER)

    print(f"Processing: {INPUT_FILE}")
    tts.process_jsonl(INPUT_FILE)

    tts.wait_until_done()
    tts.close()

    print("Done.")