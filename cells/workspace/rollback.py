"""
cells/workspace/rollback.py — Snapshot + Time-Travel
"""
from __future__ import annotations
import shutil
import uuid
from pathlib import Path
from typing import Dict
from kernel.config import settings


class RollbackManager:
    """Directory snapshots and time-travel restore."""
    
    def __init__(self, rollback_dir: str = "data/rollback"):
        self.rollback_dir = Path(rollback_dir)
        self.rollback_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: Dict[str, Path] = {}
    
    async def snapshot(self) -> str:
        snap_id = str(uuid.uuid4())
        snap_path = self.rollback_dir / snap_id
        root = settings.workspace_root
        if root.exists():
            shutil.copytree(root, snap_path, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        self._snapshots[snap_id] = snap_path
        return snap_id
    
    async def restore(self, snapshot_id: str) -> bool:
        snap_path = self._snapshots.get(snapshot_id)
        if not snap_path or not snap_path.exists():
            return False
        root = settings.workspace_root
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(snap_path, root)
        return True
