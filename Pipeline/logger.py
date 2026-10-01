"""

Format:
    log(time_str, process_name, data)

The logger creates a unique log file per program run
and saves it to the directory specified by LOGS_PATH in paths.json.
"""

import os
import sys
from datetime import datetime

# Insert project root to sys.path to allow importing config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from config.load_paths import load_paths
except ImportError:
    # Fallback to empty paths dict if import fails for any reason
    def load_paths():
        return {}

# Generate a unique run-time string for the filename
_run_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
_log_filename = f"log_{_run_time_str}.txt"
_log_file_path = None

def _init_logger():
    global _log_file_path
    if _log_file_path is not None:
        return _log_file_path

    paths = load_paths()
    logs_dir = paths.get("LOGS_PATH")
    
    if not logs_dir:
        logs_dir = os.path.join(project_root, "Logs")
        
    # Makes a new folder for each day with the format being mm-dd-yyyy
    date_dir = datetime.now().strftime("%m-%d-%Y")
    logs_dir = os.path.join(logs_dir, date_dir)
        
    os.makedirs(logs_dir, exist_ok=True)
    _log_file_path = os.path.join(logs_dir, _log_filename)
    return _log_file_path


def log(str1: str, str2: str, exec_time: float = None):
    """
    Logs data to a run-specific text file.

    Parameters:
    - (time): The time the event occurred.
    - str1 (process name): The process or source of the logic.
    - str2 (data): The data or message to log.
    - exec_time (optional): The execution time of the process, if applicable.
    """
    file_path = _init_logger()
    time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if exec_time is not None:
        log_entry = f"[{time_str}] {str1} ({exec_time:.6f}s): [{str2}]\n"
    else:
        log_entry = f"[{time_str}] [{str1}]: [{str2}]\n"

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(log_entry)