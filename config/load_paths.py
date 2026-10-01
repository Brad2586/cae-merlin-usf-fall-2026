import json
from pathlib import Path

def load_paths() -> dict:
    """
    Loads paths from paths.json, resolves them relative to project root,
    and converts all paths to strings for compatibility with external libraries.
    """
    # Detect project root (assumes config folder is inside project root)
    base_dir = Path(__file__).resolve().parent.parent

    # Load JSON
    with open(base_dir / "config" / "paths.json", "r") as f:
        raw_paths = json.load(f)

    # Convert everything to absolute strings
    paths = {}
    for key, val in raw_paths.items():
        if isinstance(val, list):
            paths[key.upper()] = [str(base_dir / p) for p in val]
        else:
            paths[key.upper()] = str(base_dir / val)

    return paths
