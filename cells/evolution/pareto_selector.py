"""
cells/evolution/pareto_selector.py — Weighted Array Index Selection
No optimization at runtime. Pre-computed weights.
"""
from typing import Dict, List, Any


class ParetoSelector:
    """Select from pre-filtered candidates using weighted scoring."""
    
    def select(self, candidates: List[Dict[str, Any]], weights: Dict[str, float]) -> Dict[str, Any]:
        if not candidates:
            return {}
        
        def score(c: Dict) -> float:
            s = 0.0
            for k, w in weights.items():
                s += c.get("params", {}).get(k, 0) * w
            return s
        
        # Deterministic: highest score wins
        return max(candidates, key=score)
