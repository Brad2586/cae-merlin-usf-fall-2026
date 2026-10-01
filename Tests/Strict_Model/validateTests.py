from llama_cpp import Llama
import time
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.load_paths import load_paths

LOG_FILE = r"Tests\Strict_Model\validationLogs.txt"

paths = load_paths()
GGUF_MODEL_PATH = paths["GGUF_MODEL_PATH_STRICT"]


model_rp = Llama(
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


def generate_from_redpajama(prompt, max_new_tokens=150):
    result = model_rp(prompt, max_tokens=max_new_tokens, temperature=0.0, echo=False)
    if 'choices' in result and len(result['choices']) > 0:
        return result['choices'][0].get('text', '')
    return str(result)


def parse_output(raw: str) -> dict:
    raw = raw.strip()
    try:
        start = raw.index('{')
        end = raw.rindex('}') + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


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


def load_test_pairs(filepath: str) -> list[tuple[str, dict]]:
    pairs = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                pairs.append((entry["input"], entry["output"]))  # entry["output"] unwraps the nested dict
            except (json.JSONDecodeError, KeyError) as ex:
                print(f"WARNING: could not parse line: {ex}, skipping.")
    return pairs


if __name__ == "__main__":
    TEST_FILE    = r"Tests\Strict_Model\testData.txt"
    RESULTS_FILE = r"Tests\Strict_Model\validationResults.txt"

    open(RESULTS_FILE, "w").close()

    passed   = 0
    failed   = 0
    errors   = 0
    failures = []

    test_pairs = load_test_pairs(TEST_FILE)
    total = len(test_pairs)

    total_start_time = time.time()

    with open(RESULTS_FILE, "a") as outfile:
        for i, (input_text, expected) in enumerate(test_pairs):
            prompt = f"input: {input_text}\noutput:"
            start = time.time()
            raw_output = generate_from_redpajama(prompt, 150)
            elapsed = time.time() - start

            actual     = parse_output(raw_output)
            ok, reason = compare(expected, actual)
            status     = "PASS" if ok else "FAIL"

            if ok:
                passed += 1
            else:
                failed += 1
                failures.append((input_text, expected, raw_output.strip(), reason))

            if ok:
                print(f"[{i+1}/{total}] PASS  ({elapsed:.2f}s)  \"{input_text}\"")
            else:
                print(f"[{i+1}/{total}] FAIL  ({elapsed:.2f}s)  \"{input_text}\"")
                print(f"         Reason   : {reason}")
                print(f"         Expected : {json.dumps(expected)}")
                print(f"         Got      : {raw_output.strip()}")

            outfile.write(f"[{status}] {input_text}\n")
           
            outfile.write(f"  Expected : {json.dumps(expected)}\n")
            outfile.write(f"  Got      : {raw_output.strip()}\n")
            outfile.write(f"  Reason   : {reason}\n")
            outfile.write(f"  Time     : {elapsed:.2f}s\n\n")

    accuracy = (passed / total * 100) if total > 0 else 0

    total_elapsed = time.time() - total_start_time

    summary_header = (
        f"\n\n{'='*50}\n"
        f"RESULTS: {passed}/{total} passed  |  {failed} failed  |  {errors} skipped\n"
        f"ACCURACY: {accuracy:.2f}%\n"
        f"TOTAL TIME: {total_elapsed:.2f}s\n"
        f"{'='*50}\n"
    )

    summary_details = ""
    if failures:
        summary_details += "\nFAILED INPUTS:\n"
        for inp, exp, got, reason in failures:
            summary_details += f"  - \"{inp}\"\n"
            summary_details += f"      reason   : {reason}\n"
            summary_details += f"      expected : {json.dumps(exp)}\n"
            summary_details += f"      got      : {got}\n"

    print(summary_header + summary_details)

    with open(RESULTS_FILE, "a") as outfile:
        outfile.write(summary_header + summary_details)

    with open(LOG_FILE, "a") as log:
        log.write(summary_header + "\n")

    print(f"\nFull results saved to {RESULTS_FILE}")
    print(f"Summary appended to {LOG_FILE}")