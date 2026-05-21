"""kernel/security/audit_logger.py — Structured audit logging for MCP operations."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


class AuditLogger:
    """Append-only JSONL audit log."""

    def __init__(self, log_dir: Path | str = "data/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.log_dir / f"audit_{int(time.time())}.jsonl"

    def log(self, event: str, details: dict[str, Any]):
        entry = {
            "t": time.time(),
            "event": event,
            "details": details,
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def log_invocation(self, preset: str, args: dict, result: dict):
        self.log("invocation", {
            "preset": preset,
            "args": {k: str(v)[:200] for k, v in args.items()},
            "status": "error" if "error" in result else "ok",
        })

    def log_violation(self, preset: str, violation: str):
        self.log("violation", {"preset": preset, "violation": violation})
