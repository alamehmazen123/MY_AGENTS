"""
cells/runtime/model_manager.py — Load/Unload/Switch State Machine
"""
from __future__ import annotations
from enum import Enum, auto
from typing import Optional
import asyncio


class ModelState(Enum):
    UNLOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ACTIVE = auto()
    UNLOADING = auto()
    ERROR = auto()


class ModelManager:
    """6-state model lifecycle."""
    
    def __init__(self):
        self._models: dict = {}
        self._active_model: Optional[str] = None
        self._lock = asyncio.Lock()
    
    async def load(self, model: str) -> bool:
        async with self._lock:
            if model not in self._models:
                self._models[model] = {"state": ModelState.UNLOADED, "load_time": 0}
            
            m = self._models[model]
            if m["state"] == ModelState.LOADED:
                m["state"] = ModelState.ACTIVE
                self._active_model = model
                return True
            
            if m["state"] == ModelState.UNLOADED:
                m["state"] = ModelState.LOADING
                # Simulate Ollama load
                await asyncio.sleep(0.05)
                m["state"] = ModelState.LOADED
                m["state"] = ModelState.ACTIVE
                self._active_model = model
                return True
            
            return False
    
    async def unload(self, model: str) -> bool:
        async with self._lock:
            m = self._models.get(model)
            if not m:
                return False
            m["state"] = ModelState.UNLOADING
            await asyncio.sleep(0.02)
            m["state"] = ModelState.UNLOADED
            if self._active_model == model:
                self._active_model = None
            return True
    
    async def unload_if_needed(self):
        """Unload non-active models to free VRAM."""
        async with self._lock:
            for model, m in list(self._models.items()):
                if m["state"] == ModelState.LOADED and model != self._active_model:
                    m["state"] = ModelState.UNLOADING
                    await asyncio.sleep(0.02)
                    m["state"] = ModelState.UNLOADED
    
    async def unload_all(self):
        async with self._lock:
            for model in list(self._models.keys()):
                await self.unload(model)
    
    async def switch(self, from_model: str, to_model: str) -> bool:
        """Switch models. Target: <30s, no VRAM leak."""
        await self.unload(from_model)
        ok = await self.load(to_model)
        return ok
    
    def get_active(self) -> Optional[str]:
        return self._active_model
