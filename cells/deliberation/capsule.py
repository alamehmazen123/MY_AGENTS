"""
cells/deliberation/capsule.py — Hard Bounds, Interruptible, Resumable
MAX_RUNTIME=45s, MAX_TOKENS=12000, MAX_ITERATIONS=4
"""
import time
from typing import Optional, Dict, Any


class Capsule:
    """Execution capsule with hard bounds."""
    
    def __init__(self, max_runtime: float = 45.0, max_tokens: int = 12000, max_iterations: int = 4):
        self.max_runtime = max_runtime
        self.max_tokens = max_tokens
        self.max_iterations = max_iterations
        self._start_time: Optional[float] = None
        self._tokens_used = 0
        self._iterations = 0
        self._active = False
    
    def begin(self, prompt: str, model: str) -> "Capsule":
        self._start_time = time.monotonic()
        self._tokens_used = 0
        self._iterations = 0
        self._active = True
        return self
    
    def end(self):
        self._active = False
    
    def check(self, tokens_delta: int = 0) -> bool:
        """Return True if execution may continue."""
        if not self._active:
            return False
        if time.monotonic() - self._start_time > self.max_runtime:
            return False
        if self._tokens_used + tokens_delta > self.max_tokens:
            return False
        if self._iterations >= self.max_iterations:
            return False
        return True
    
    def consume(self, tokens: int):
        self._tokens_used += tokens
        self._iterations += 1
    
    @property
    def remaining_time(self) -> float:
        if not self._start_time:
            return self.max_runtime
        return max(0, self.max_runtime - (time.monotonic() - self._start_time))
    
    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self._tokens_used)
    
    @property
    def remaining_iterations(self) -> int:
        return max(0, self.max_iterations - self._iterations)
    
    def status(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "elapsed": time.monotonic() - self._start_time if self._start_time else 0,
            "tokens_used": self._tokens_used,
            "iterations": self._iterations,
            "remaining_time": self.remaining_time,
            "remaining_tokens": self.remaining_tokens,
            "remaining_iterations": self.remaining_iterations,
        }
