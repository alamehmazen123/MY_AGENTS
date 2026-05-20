"""
cells/workspace/transactions.py — Atomic Temp-File-Then-Rename
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict
import tempfile
import os


class TransactionManager:
    """Atomic file writes via temp-then-rename."""
    
    async def write(self, target: Path, content: str) -> Dict:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp_")
            try:
                os.write(fd, content.encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(tmp, target)
            return {"status": "written", "path": str(target)}
        except Exception as e:
            return {"error": str(e)}
