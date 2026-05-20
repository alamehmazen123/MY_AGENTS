"""
plasma/recovery_journal.py — Every Recovery Logged
"""
from pathlib import Path
import json
from datetime import datetime
from kernel.config import settings


class RecoveryJournal:
    """Log all recovery attempts."""
    
    def __init__(self):
        self.file = settings.data_dir / "recovery_journal.jsonl"
    
    def log(self, mode: str, result: str, elapsed_ms: float):
        with open(self.file, "a", encoding="utf-8") as f:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "mode": mode,
                "result": result,
                "elapsed_ms": elapsed_ms,
            }
            f.write(json.dumps(entry) + "\n")


journal = RecoveryJournal()
