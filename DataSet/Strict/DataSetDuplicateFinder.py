import json

input_file = "DataSet/Strict/Data_Strict.jsonl"
output_file = "DataSet/Strict/Data_clean.jsonl"

seen = set()
duplicates_removed = 0

with open(input_file, "r") as f_in, open(output_file, "w") as f_out:
    for line_number, line in enumerate(f_in, 1):
        line = line.strip()

        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON on line {line_number}")
            continue

        normalized = json.dumps(data, sort_keys=True)

        if normalized in seen:
            duplicates_removed += 1
            continue

        seen.add(normalized)
        f_out.write(json.dumps(data) + "\n")

print(f"Finished. Removed {duplicates_removed} duplicate entries.")