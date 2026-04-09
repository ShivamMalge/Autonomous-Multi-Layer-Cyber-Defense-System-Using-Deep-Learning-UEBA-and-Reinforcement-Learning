import json
import os
import logging

def load_events(file_path: str, limit: int = 50000) -> list:
    """Loads events from the JSONL log file into a memory list."""
    if not os.path.exists(file_path):
        logging.error(f"Event file not found at {file_path}")
        return []
        
    events = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                if line.strip():
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logging.error(f"Failed to load events: {e}")
        
    return events
