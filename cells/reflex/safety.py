"""
cells/reflex/safety.py — Invariant Verification (Lookup Only)
No computation. Pure table lookup.
"""
from typing import Set
from kernel.lattice_verifier import LATTICE


class SafetyChecker:
    """Lookup-only safety verification."""
    
    REQUIRED = {"reflex_deterministic", "single_runtime"}
    
    def check(self, active: Set[str]) -> bool:
        closed = set(active)
        changed = True
        while changed:
            changed = False
            for inv in list(closed):
                for implied in LATTICE.get(inv, {}).get("implies", []):
                    if implied not in closed:
                        closed.add(implied)
                        changed = True
        return self.REQUIRED.issubset(closed)
    
    def missing(self, active: Set[str]) -> Set[str]:
        closed = set(active)
        changed = True
        while changed:
            changed = False
            for inv in list(closed):
                for implied in LATTICE.get(inv, {}).get("implies", []):
                    if implied not in closed:
                        closed.add(implied)
                        changed = True
        return self.REQUIRED - closed
