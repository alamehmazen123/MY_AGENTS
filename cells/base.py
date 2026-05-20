"""
cells/base.py — Cell Lifecycle, Metabolism, Apoptosis
All cells inherit from BaseCell.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any
from enum import Enum, auto


class CellState(Enum):
    DORMANT = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    DEGRADED = auto()
    PAUSED = auto()
    APOPTOSIS = auto()
    DEAD = auto()


class BaseCell(ABC):
    """Abstract base for all living cells."""
    
    def __init__(self, name: str):
        self.name = name
        self.state = CellState.DORMANT
        self.metrics: Dict[str, Any] = {}
        self._invariants: list[str] = []
    
    async def init(self) -> None:
        self.state = CellState.INITIALIZING
        await self._on_init()
        self.state = CellState.ACTIVE
    
    async def shutdown(self) -> None:
        self.state = CellState.APOPTOSIS
        await self._on_shutdown()
        self.state = CellState.DEAD
    
    async def degrade(self, reason: str) -> None:
        self.state = CellState.DEGRADED
        self.metrics["degraded_reason"] = reason
        await self._on_degrade(reason)
    
    async def pause(self) -> None:
        if self.state == CellState.ACTIVE:
            self.state = CellState.PAUSED
            await self._on_pause()
    
    async def resume(self) -> None:
        if self.state == CellState.PAUSED:
            self.state = CellState.ACTIVE
            await self._on_resume()
    
    def invariant_holds(self, invariant: str) -> bool:
        return invariant in self._invariants
    
    @abstractmethod
    async def _on_init(self) -> None:
        pass
    
    @abstractmethod
    async def _on_shutdown(self) -> None:
        pass
    
    async def _on_degrade(self, reason: str) -> None:
        pass
    
    async def _on_pause(self) -> None:
        pass
    
    async def _on_resume(self) -> None:
        pass
