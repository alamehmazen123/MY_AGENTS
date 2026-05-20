"""
cells/runtime/circuit_breaker.py — Predictive Failure Detection
"""
import time
from typing import Dict, Any


class CircuitBreaker:
    """Graduated response to model failures."""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state: Dict[str, Dict[str, Any]] = {}
    
    def is_open(self, model: str) -> bool:
        s = self._state.get(model, {"failures": 0, "last_failure": 0, "open": False})
        if s["open"]:
            if time.time() - s["last_failure"] > self.recovery_timeout:
                s["open"] = False
                s["failures"] = 0
                return False
            return True
        return False
    
    def record_failure(self, model: str):
        s = self._state.setdefault(model, {"failures": 0, "last_failure": 0, "open": False})
        s["failures"] += 1
        s["last_failure"] = time.time()
        if s["failures"] >= self.failure_threshold:
            s["open"] = True
    
    def record_success(self, model: str):
        s = self._state.get(model)
        if s:
            s["failures"] = 0
            s["open"] = False
