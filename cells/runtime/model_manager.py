"""cells/runtime/model_manager.py — Real Ollama model lifecycle with load/unload verification."""
from __future__ import annotations
from enum import Enum, auto
from typing import Optional
import asyncio
import httpx
from kernel.config import settings


class ModelState(Enum):
    UNLOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ACTIVE = auto()
    UNLOADING = auto()
    ERROR = auto()


class ModelManager:
    """6-state model lifecycle with real Ollama integration."""

    def __init__(self):
        self._models: dict = {}
        self._active_model: Optional[str] = None
        self._lock = asyncio.Lock()

    async def _ollama_ps(self) -> list[str]:
        """Query Ollama for currently loaded models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(f"{settings.ollama_host}/api/ps")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", m.get("model", "")) for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def _ollama_unload(self, model: str) -> bool:
        """Force-unload a model from Ollama by generating with keep_alive=0."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "model": model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0,
                }
                await client.post(
                    f"{settings.ollama_host}/api/generate",
                    json=payload,
                    timeout=30,
                )
                # Verify unload
                for _ in range(10):
                    await asyncio.sleep(0.3)
                    running = await self._ollama_ps()
                    if model not in running:
                        return True
                return model not in await self._ollama_ps()
        except Exception:
            return False

    async def load(self, model: str) -> bool:
        async with self._lock:
            if model not in self._models:
                self._models[model] = {"state": ModelState.UNLOADED, "load_time": 0}

            m = self._models[model]
            if m["state"] == ModelState.ACTIVE:
                return True

            # Check if Ollama already has it loaded
            running = await self._ollama_ps()
            if model in running:
                m["state"] = ModelState.LOADED
                m["state"] = ModelState.ACTIVE
                self._active_model = model
                return True

            m["state"] = ModelState.LOADING
            # Ollama loads on first use; we just verify it's available
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    res = await client.post(
                        f"{settings.ollama_host}/api/generate",
                        json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
                        timeout=30,
                    )
                    if res.status_code == 200:
                        m["state"] = ModelState.ACTIVE
                        self._active_model = model
                        return True
                    m["state"] = ModelState.ERROR
                    return False
            except Exception:
                m["state"] = ModelState.ERROR
                return False

    async def unload(self, model: str) -> bool:
        async with self._lock:
            m = self._models.get(model)
            if not m:
                return False
            m["state"] = ModelState.UNLOADING
            ok = await self._ollama_unload(model)
            m["state"] = ModelState.UNLOADED if ok else ModelState.ERROR
            if self._active_model == model:
                self._active_model = None
            return ok

    async def unload_if_needed(self):
        """Unload all non-active models."""
        async with self._lock:
            for model, m in list(self._models.items()):
                if model != self._active_model and m["state"] != ModelState.UNLOADED:
                    await self._ollama_unload(model)
                    m["state"] = ModelState.UNLOADED

    async def unload_all(self):
        async with self._lock:
            for model in list(self._models.keys()):
                await self._ollama_unload(model)
                self._models[model]["state"] = ModelState.UNLOADED
            self._active_model = None

    async def verify_zero_loaded(self) -> dict:
        """Verify no models are loaded in Ollama."""
        running = await self._ollama_ps()
        return {
            "zero_loaded": len(running) == 0,
            "running_models": running,
            "active_model": self._active_model,
        }

    async def switch(self, from_model: str, to_model: str) -> bool:
        """Switch models: unload from, load to, verify zero in between."""
        await self.unload(from_model)
        # Verify zero loaded
        verify = await self.verify_zero_loaded()
        if not verify["zero_loaded"]:
            # Force unload any remaining
            for m in verify["running_models"]:
                await self._ollama_unload(m)
        ok = await self.load(to_model)
        return ok

    def get_active(self) -> Optional[str]:
        return self._active_model

    def state_summary(self) -> dict:
        return {
            "active_model": self._active_model,
            "tracked_models": {
                k: v["state"].name for k, v in self._models.items()
            },
        }
