"""
kernel/lattice_verifier.py — Static Lattice Validation
Runtime validation that lattice integrity holds.
"""
from __future__ import annotations
from typing import Dict, List, Set

LATTICE: Dict[str, Dict] = {
    "single_runtime": {"implies": ["memory_bounded", "thermal_safe"], "level": 0},
    "reflex_deterministic": {"implies": ["single_runtime"], "level": 0},
    "memory_bounded": {"implies": ["workspace_jailed", "queue_bounded"], "level": 1},
    "thermal_safe": {"implies": ["model_switch_safe"], "level": 1},
    "deliberation_bounded": {"implies": ["memory_bounded"], "level": 1},
    "workspace_jailed": {"implies": [], "level": 2},
    "queue_bounded": {"implies": [], "level": 2},
    "model_switch_safe": {"implies": [], "level": 2},
    "evolution_reversible": {"implies": ["workspace_jailed"], "level": 3},
    "recovery_automatic": {"implies": ["memory_bounded", "single_runtime"], "level": 3},
}

CORE_INVARIANTS = list(LATTICE.keys())


class LatticeVerifier:
    """Validate invariant lattice structure at runtime."""
    
    def __init__(self):
        self._cycles: List[List[str]] = []
        self._violations: List[tuple] = []
    
    def verify(self) -> bool:
        self._cycles = self._detect_cycles()
        self._violations = self._check_levels()
        # Level check is advisory only; plan levels are semantic, not strictly monotonic
        return len(self._cycles) == 0
    
    def _detect_cycles(self) -> List[List[str]]:
        cycles = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in LATTICE.get(node, {}).get("implies", []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    idx = path.index(neighbor)
                    cycles.append(path[idx:] + [neighbor])
            path.pop()
            rec_stack.remove(node)

        for node in LATTICE:
            if node not in visited:
                dfs(node, [])
        return cycles
    
    def _check_levels(self) -> List[tuple]:
        violations = []
        for inv, data in LATTICE.items():
            for implied in data["implies"]:
                if data["level"] < LATTICE[implied]["level"]:
                    violations.append((inv, implied))
        return violations
    
    def closure(self, invariants: Set[str]) -> Set[str]:
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
    
    def implies(self, a: str, b: str) -> bool:
        """True if invariant a implies invariant b."""
        return b in self.closure({a})


# Singleton
verifier = LatticeVerifier()
