import json

file_path = "Data_Lenient.jsonl"

with open(file_path, "r") as f:
    for i, line in enumerate(f, 1):
        # Check raw line (fastest way)
        if "error" in line.lower() and "?" in line:
            print(f"Match on line {i}: {line.strip()}")