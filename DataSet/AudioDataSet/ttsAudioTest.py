import os
import sys
import json
import time
import wave
from pathlib import Path

import numpy as np
import scipy.signal
from faster_whisper import WhisperModel

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.load_paths import load_paths

from llama_cpp import Llama

paths = load_paths()

LOG_FILE     = r"Tests\Audio_Model\validationLogs.txt"
RESULTS_FILE = r"Tests\Audio_Model\validationResults.txt"
WAV_ROOT     = r"./DataSet/AudioDataSet/wav_outputs"


# ---------------------------------------------------
# WAV loader
# ---------------------------------------------------
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


# ---------------------------------------------------
# Transcribe a float32 numpy array at 16kHz
# ---------------------------------------------------
def transcribe(fw: WhisperModel, audio: np.ndarray) -> str:
    segments, _ = fw.transcribe(
        audio,
        language="en",
        beam_size=1,
        vad_filter=False,
    )
    return "".join(seg.text for seg in segments)


# ---------------------------------------------------
# Collect all .wav / .json pairs under wav_root
# ---------------------------------------------------
def collect_pairs(wav_root: str) -> list[tuple[Path, Path]]:
    pairs = []
    for wav_path in sorted(Path(wav_root).rglob("*.wav")):
        json_path = wav_path.with_suffix(".json")
        if json_path.exists():
            pairs.append((wav_path, json_path))
        else:
            print(f"WARNING: no matching .json for {wav_path}, skipping.")
    return pairs


GGUF_MODEL_PATH = paths["GGUF_MODEL_PATH_STRICT"]

strict_model_llm = Llama(
    model_path=GGUF_MODEL_PATH,
    n_ctx=2048,
    n_threads=10,
    seed=42,
    n_gpu_layers=-1,
    n_batch=512,
    n_ubatch=512,
    low_vram=False,
    cache=True,
    use_mmap=True,
    use_mlock=True
)



def generate_from_llm(prompt, max_new_tokens=135):
    start_time = time.time()
    result = strict_model_llm(prompt, max_tokens=max_new_tokens, temperature=0.0, echo=False)
    elapsed = time.time() - start_time

    if 'choices' in result and len(result['choices']) > 0:
        text = result['choices'][0].get('text', '')
    else:
        text = str(result)

    usage = result.get('usage', {})
    print(f"time: {elapsed:.2f}s", f"usage={usage}")
    return text


# ---------------------------------------------------
# Parse LLM raw text → dict
# ---------------------------------------------------
def parse_output(raw: str) -> dict | None:
    raw = raw.strip()
    try:
        start = raw.index('{')
        end   = raw.rindex('}') + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


# ---------------------------------------------------
# Compare expected vs actual
# ---------------------------------------------------
def compare(expected: dict, actual: dict) -> tuple[bool, str]:
    if actual is None:
        return False, "could not parse model output as JSON"

    if expected.get("Type") != actual.get("Type"):
        return False, f"Type mismatch: expected '{expected.get('Type')}' got '{actual.get('Type')}'"

    typ = expected.get("Type")

    if typ in ("command", "clarification"):
        exp_keys = expected.get("parameters_keys") or []
        act_keys = actual.get("parameters_keys") or []
        exp_vals = expected.get("parameters_values") or []
        act_vals = actual.get("parameters_values") or []

        if exp_keys != act_keys:
            return False, f"parameters_keys mismatch: expected {exp_keys} got {act_keys}"
        if exp_vals != act_vals:
            return False, f"parameters_values mismatch: expected {exp_vals} got {act_vals}"

        if typ == "clarification":
            exp_msg = (expected.get("message") or "").strip().lower()
            act_msg = (actual.get("message") or "").strip().lower()
            if exp_msg != act_msg:
                return False, f"message mismatch: expected '{exp_msg}' got '{act_msg}'"

    elif typ in ("error", "exit"):
        pass

    return True, "OK"


# ---------------------------------------------------
# Main
# ---------------------------------------------------
if __name__ == "__main__":
    import torch

    device       = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    fw = WhisperModel(
        "small.en",
        device=device,
        compute_type=compute_type,
    )

    pairs = collect_pairs(WAV_ROOT)
    total = len(pairs)

    if total == 0:
        print(f"No .wav/.json pairs found under {WAV_ROOT}")
        sys.exit(0)

    passed   = 0
    failed   = 0
    failures = []

    total_start = time.time()
    total_llm_time = 0.0
    total_transcribe_time = 0.0

    os.makedirs(Path(RESULTS_FILE).parent, exist_ok=True)
    os.makedirs(Path(LOG_FILE).parent,     exist_ok=True)
    open(RESULTS_FILE, "w").close()

    with open(RESULTS_FILE, "a") as outfile:
        for i, (wav_path, json_path) in enumerate(pairs):

            with open(json_path, "r", encoding="utf-8") as f:
                entry    = json.load(f)
                expected = entry["output"]

            start         = time.time()
            audio         = load_wav_as_float32(wav_path)

            # Transcription timing
            t0 = time.time()
            transcription = transcribe(fw, audio).strip().lower()
            transcribe_elapsed = time.time() - t0
            total_transcribe_time += transcribe_elapsed

            # LLM timing
            t0 = time.time()
            prompt     = f"input: {transcription}\noutput:"
            raw_output = generate_from_llm(prompt, max_new_tokens=135)
            llm_elapsed = time.time() - t0
            total_llm_time += llm_elapsed

            elapsed    = time.time() - start

            actual     = parse_output(raw_output)
            ok, reason = compare(expected, actual)
            status     = "PASS" if ok else "FAIL"

            if ok:
                passed += 1
            else:
                failed += 1
                failures.append((str(wav_path), transcription, expected, raw_output.strip(), reason))

            if ok:
                print(f"[{i+1}/{total}] PASS  ({elapsed:.2f}s)  {wav_path.name}")
            else:
                print(f"[{i+1}/{total}] FAIL  ({elapsed:.2f}s)  {wav_path.name}")
                print(f"         Transcript : {transcription}")
                print(f"         Reason     : {reason}")
                print(f"         Expected   : {json.dumps(expected)}")
                print(f"         Got        : {raw_output.strip()}")

            outfile.write(f"[{status}] {wav_path}\n")
            outfile.write(f"  Transcript : {transcription}\n")
            outfile.write(f"  Expected   : {json.dumps(expected)}\n")
            outfile.write(f"  Got        : {raw_output.strip()}\n")
            outfile.write(f"  Reason     : {reason}\n")
            outfile.write(f"  Time       : {elapsed:.2f}s\n\n")

    total_elapsed = time.time() - total_start
    avg_llm_time = total_llm_time / total if total > 0 else 0
    avg_transcribe_time = total_transcribe_time / total if total > 0 else 0
    accuracy = (passed / total * 100) if total > 0 else 0

    summary_header = (
        f"\n\n{'='*50}\n"
        f"RESULTS: {passed}/{total} passed  |  {failed} failed\n"
        f"ACCURACY: {accuracy:.2f}%\n"
        f"TOTAL TIME: {total_elapsed:.2f}s\n"
        f"AVG LLM TIME: {avg_llm_time:.2f}s\n"
        f"AVG TRANSCRIPTION TIME: {avg_transcribe_time:.2f}s\n"
        f"{'='*50}\n"
    )

    summary_details = ""
    if failures:
        summary_details += "\nFAILED INPUTS:\n"
        for wav, transcript, exp, got, reason in failures:
            summary_details += f"  - {wav}\n"
            summary_details += f"      transcript : {transcript}\n"
            summary_details += f"      reason     : {reason}\n"
            summary_details += f"      expected   : {json.dumps(exp)}\n"
            summary_details += f"      got        : {got}\n"

    print(summary_header + summary_details)

    with open(RESULTS_FILE, "a") as outfile:
        outfile.write(summary_header + summary_details)

    with open(LOG_FILE, "a") as log:
        log.write(summary_header + "\n")

    print(f"\nFull results saved to {RESULTS_FILE}")
    print(f"Summary appended to {LOG_FILE}")