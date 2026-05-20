"""
plasma/snapshots.py — Delta Snapshots, 30s Interval
"""
from pathlib import Path
from typing import List, Dict
import json
from kernel.config import settings


class SnapshotStore:
    """Manage delta snapshots."""
    
    def __init__(self):
        self.dir = settings.data_dir / "snapshots"
        self.dir.mkdir(parents=True, exist_ok=True)
    
    def list(self) -> List[Dict]:
        snaps = []
        for f in sorted(self.dir.glob("snapshot_*.json")):
            snaps.append({"name": f.name, "size": f.stat().st_size})
        return snaps


snapshots = SnapshotStore()
