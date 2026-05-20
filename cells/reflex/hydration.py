"""
cells/reflex/hydration.py — Pre-Computed State Cache
Instant data serving. No computation at request time.
"""
from typing import Dict, Any, Optional
import time


class HydrationCache:
    """Pre-computed hydration cache with TTL."""
    
    def __init__(self, default_ttl_seconds: float = 5.0):
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._default_ttl = default_ttl_seconds
        self._hits = 0
        self._misses = 0
    
    def preload(self, key: str, value: Any, ttl: Optional[float] = None):
        self._cache[key] = value
        self._ttl[key] = time.monotonic() + (ttl or self._default_ttl)
    
    def get(self, key: str) -> Any:
        now = time.monotonic()
        expire = self._ttl.get(key, 0)
        if now > expire:
            self._misses += 1
            return None
        self._hits += 1
        return self._cache.get(key)
    
    def invalidate(self, key: str):
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
    
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
            "size": len(self._cache),
        }
