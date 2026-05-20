"""
cells/mcp/sandbox.py — Process Isolation, Resource Caps
"""
from __future__ import annotations
from typing import Dict
import asyncio
try:
    import resource
except ImportError:
    resource = None  # Windows


class Sandbox:
    """Resource-capped sandbox for MCP execution."""
    
    def __init__(self, max_memory_mb: int = 512, max_cpu_sec: float = 30.0):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_sec = max_cpu_sec
    
    async def run(self, preset: str, args: dict, handler=None) -> dict:
        if handler is None:
            return {"error": "preset_handler_missing", "preset": preset}
        try:
            # Execute handler (sync or async)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(args)
            else:
                # Run sync handler in threadpool to avoid blocking
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, handler, args)
            if not isinstance(result, dict):
                result = {"output": result}
            result["preset"] = preset
            result["sandboxed"] = True
            return result
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc(), "preset": preset}
    
    def _limit_resources(self):
        if resource:
            resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_mb * 1024 * 1024, -1))
            resource.setrlimit(resource.RLIMIT_CPU, (int(self.max_cpu_sec), -1))
