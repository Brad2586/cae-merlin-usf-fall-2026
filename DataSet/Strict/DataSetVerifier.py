import json

# Files
ACCEPTABLE_FILE = "DataSet/AcceptableParameters.txt"
DATASET_FILE = "DataSet/Strict/Data_Strict.jsonl"   # your dataset file

def load_acceptable_parameters(filepath):
    """Load acceptable parameter keys into a set."""
    with open(filepath, "r") as f:
        return set(line.strip() for line in f if line.strip())

def validate_dataset(dataset_file, valid_keys):
    invalid_entries = []

    with open(dataset_file, "r") as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                print(f"Invalid JSON on line {line_number}")
                continue

            output = data.get("output", {})
            keys = output.get("parameters_keys", [])

            for key in keys:
                if key not in valid_keys:
                    invalid_entries.append((line_number, key))

    return invalid_entries


def main():
    valid_keys = load_acceptable_parameters(ACCEPTABLE_FILE)
    invalid = validate_dataset(DATASET_FILE, valid_keys)

    if not invalid:
        print("All parameter keys are valid.")
    else:
        print("Invalid parameter keys found:")
        for line, key in invalid:
            print(f"Line {line}: {key}")


if __name__ == "__main__":
    main()