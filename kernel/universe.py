"""
kernel/universe.py — StateUniverse, Reactive Observation
Single source of truth for all runtime state.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
import copy


@dataclass
class StateSnapshot:
    timestamp: datetime
    data: Dict[str, Any]
    checksum: str = ""


class StateUniverse:
    """Central reactive state container. All mutations flow through here."""
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._listeners: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
        self._global_listeners: List[Callable[[str, Any, Any], None]] = []
        self._lock = asyncio.Lock()
        self._mutation_count = 0
    
    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return copy.deepcopy(self._state.get(key, default))
    
    async def get_all(self) -> Dict[str, Any]:
        async with self._lock:
            return copy.deepcopy(self._state)
    
    async def set(self, key: str, value: Any, silent: bool = False) -> None:
        async with self._lock:
            old = self._state.get(key)
            self._state[key] = copy.deepcopy(value)
            self._mutation_count += 1
        if not silent:
            await self._notify(key, old, value)
    
    async def update(self, patch: Dict[str, Any], silent: bool = False) -> None:
        async with self._lock:
            old_pairs = {}
            for key, value in patch.items():
                old_pairs[key] = self._state.get(key)
                self._state[key] = copy.deepcopy(value)
            self._mutation_count += len(patch)
        if not silent:
            for key, old in old_pairs.items():
                await self._notify(key, old, patch[key])
    
    async def delete(self, key: str) -> None:
        async with self._lock:
            old = self._state.pop(key, None)
            self._mutation_count += 1
        await self._notify(key, old, None)
    
    def subscribe(self, key: str, callback: Callable[[str, Any, Any], None]) -> Callable[[], None]:
        self._listeners.setdefault(key, []).append(callback)
        def unsubscribe():
            self._listeners[key].remove(callback)
        return unsubscribe
    
    def subscribe_all(self, callback: Callable[[str, Any, Any], None]) -> Callable[[], None]:
        self._global_listeners.append(callback)
        def unsubscribe():
            self._global_listeners.remove(callback)
        return unsubscribe
    
    async def _notify(self, key: str, old: Any, new: Any) -> None:
        for cb in self._listeners.get(key, []):
            try:
                cb(key, old, new)
            except Exception:
                pass
        for cb in self._global_listeners:
            try:
                cb(key, old, new)
            except Exception:
                pass
    
    def snapshot(self) -> StateSnapshot:
        import hashlib, json
        data = copy.deepcopy(self._state)
        payload = json.dumps(data, sort_keys=True, default=str)
        checksum = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return StateSnapshot(timestamp=datetime.utcnow(), data=data, checksum=checksum)
    
    @property
    def mutation_count(self) -> int:
        return self._mutation_count


# Singleton
universe = StateUniverse()
