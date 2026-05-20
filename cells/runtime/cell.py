"""
cells/runtime/cell.py — RuntimeCell: Single Model Enforcement
6-state machine, mutex enforcement.
"""
from __future__ import annotations
import asyncio
from cells.base import BaseCell, CellState
from kernel.events import bus
from kernel.config import settings


class RuntimeCell(BaseCell):
    """
    Runtime layer: single-model execution with predictive health.
    Enforces: only one model active at any time.
    """
    
    def __init__(self):
        super().__init__("runtime")
        self._invariants = ["single_runtime", "memory_bounded", "thermal_safe", "model_switch_safe", "queue_bounded"]
        self._queue = None
        self._model_manager = None
        self._stream_buffer = None
        self._circuit_breaker = None
        self._thermal_monitor = None
        self._model_lock = asyncio.Lock()
    
    async def _on_init(self):
        from cells.runtime.queue import SprintQueue
        from cells.runtime.model_manager import ModelManager
        from cells.runtime.stream_buffer import StreamBuffer
        from cells.runtime.circuit_breaker import CircuitBreaker
        from cells.runtime.thermal_monitor import ThermalMonitor
        self._queue = SprintQueue()
        self._model_manager = ModelManager()
        self._stream_buffer = StreamBuffer()
        self._circuit_breaker = CircuitBreaker()
        self._thermal_monitor = ThermalMonitor()
        await bus.emit("cell.runtime.ready", {})
    
    async def enqueue(self, task: dict) -> str:
        """Enqueue a task. Returns task ID."""
        return await self._queue.enqueue(task)
    
    async def run_task(self, task_id: str) -> dict:
        """Execute a task with single-model mutex."""
        async with self._model_lock:
            task = self._queue.get(task_id)
            if not task:
                return {"error": "task_not_found"}
            
            model = task["model"]
            
            # Circuit breaker check
            if self._circuit_breaker.is_open(model):
                return {"error": "circuit_open", "model": model}
            
            # Thermal check
            if self._thermal_monitor.over_threshold():
                return {"error": "thermal_throttle"}
            
            # Load model
            ok = await self._model_manager.load(model)
            if not ok:
                self._circuit_breaker.record_failure(model)
                return {"error": "model_load_failed"}
            
            # Execute with stream buffering
            result = await self._execute_with_buffer(task)
            
            # Cleanup
            await self._model_manager.unload_if_needed()
            return result
    
    async def _execute_with_buffer(self, task: dict) -> dict:
        prompt = task["prompt"]
        model = task["model"]
        
        # Real implementation: stream from Ollama through buffer
        self._stream_buffer.start()
        
        # Simulated execution
        await asyncio.sleep(0.1)
        output = f"[Executed via {model}] {prompt[:50]}..."
        
        self._stream_buffer.end()
        return {"output": output, "tokens": len(output.split()), "model": model}
    
    async def switch_model(self, from_model: str, to_model: str) -> bool:
        """Switch active model. Must complete <30s, no VRAM leak."""
        async with self._model_lock:
            return await self._model_manager.switch(from_model, to_model)
    
    async def _on_shutdown(self):
        async with self._model_lock:
            await self._model_manager.unload_all()
        await bus.emit("cell.runtime.offline", {})
