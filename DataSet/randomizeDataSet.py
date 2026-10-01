import json
import random

INPUT_FILE  = "DataSet\dataset.jsonl"
OUTPUT_FILE = "DataSet\dataset_shuffled.jsonl"
SEED        = 12  # Set to an integer for reproducible shuffles, e.g. 42


def randomize_jsonl(input_path: str, output_path: str, seed: int = None):
    # Load all lines
    with open(input_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Parse and validate each line as JSON
    records = []
    for i, line in enumerate(lines, 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"Warning: Skipping invalid JSON on line {i}: {e}")

    # Shuffle
    if seed is not None:
        random.seed(seed)
    random.shuffle(records)

    # Write shuffled records
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print(f"Shuffled {len(records)} records -> {output_path}")
    if seed is not None:
        print(f"Seed used: {seed} (use same seed to reproduce this shuffle)")


if __name__ == "__main__":
    randomize_jsonl(INPUT_FILE, OUTPUT_FILE, SEED)