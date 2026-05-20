"""
kernel/resolution_table.py — O(1) Hash Lookup Runtime Resolution
Loads pre-computed resolution table. Zero solving at runtime.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List


class ResolutionTable:
    """O(1) resolution via pre-computed table lookup."""
    
    def __init__(self, table_path: str = "build/outputs/resolution_table.json"):
        self._table: Dict[str, Dict[str, Any]] = {}
        self._path = Path(table_path)
        self._load()
    
    def _load(self):
        if not self._path.exists():
            raise RuntimeError(f"Resolution table not found: {self._path}")
        with open(self._path, "r", encoding="utf-8") as f:
            self._table = json.load(f)
    
    def lookup(self, active_invariants: List[str], pressure: str, task: str) -> Dict[str, Any]:
        """
        Runtime resolution: O(1) hash lookup.
        active_invariants: list of invariant names (will be closed downward)
        pressure: NORMAL | ELEVATED | HIGH | CRITICAL
        task: REASONING | CODING | CHAT | REFLEX
        """
        closed = self._closure(set(active_invariants))
        key = f"{sorted(closed)}|{pressure}|{task}"
        return self._table.get(key, {
            "status": "UNKNOWN",
            "actions": ["log_anomaly"],
            "active": sorted(closed),
            "pressure": pressure,
            "task": task,
        })
    
    def _closure(self, invariants: set) -> set:
        from kernel.lattice_verifier import LATTICE
        closed = set(invariants)
        changed = True
        while changed:
            changed = False
            for inv in list(closed):
                for implied in LATTICE.get(inv, {}).get("implies", []):
                    if implied not in closed:
                        closed.add(implied)
                        changed = True
        return closed
    
    @property
    def size(self) -> int:
        return len(self._table)


# Singleton
table = ResolutionTable()
