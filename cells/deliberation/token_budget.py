"""
cells/deliberation/token_budget.py — Pre-Allocation, No Overflow
"""
from typing import Optional


class TokenBudget:
    """Pre-allocated token budget. Cannot exceed limit."""
    
    def __init__(self, limit: int):
        self.limit = limit
        self._allocated = 0
        self._consumed = 0
    
    def allocate(self, requested: int) -> bool:
        """Pre-allocate tokens before work begins."""
        if self._allocated + requested > self.limit:
            return False
        self._allocated += requested
        return True
    
    def consume(self, actual: int):
        """Consume allocated tokens."""
        self._consumed += min(actual, self._allocated)
        self._allocated -= min(actual, self._allocated)
    
    def release(self, amount: int):
        """Release unused allocation."""
        self._allocated = max(0, self._allocated - amount)
    
    @property
    def remaining(self) -> int:
        return self.limit - self._consumed - self._allocated
    
    @property
    def available(self) -> int:
        return self.limit - self._consumed
