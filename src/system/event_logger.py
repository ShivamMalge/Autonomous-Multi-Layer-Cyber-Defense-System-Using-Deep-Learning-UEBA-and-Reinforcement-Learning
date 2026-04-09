import os
import json
import logging
from datetime import datetime

class CentralEventLogger:
    """
    Single source of truth for system events.
    Appends events as JSON lines for easy dashboard/SIEM integration.
    """
    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "system_events.jsonl")
        
    def log_event(self, event: dict):
        """Log a Unified Event Schema dictionary as JSONL."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logging.error(f"Failed to log event: {e}")
