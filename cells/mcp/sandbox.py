"""cells/mcp/sandbox.py — DEPRECATED: replaced by ProcessExecutor.
Kept for backwards-compat imports; delegates to kernel.mcp.runtime."""
from __future__ import annotations
from kernel.mcp.runtime.process_executor import ProcessExecutor
from kernel.mcp.protocol.tool_definition import ToolDefinition


class Sandbox:
    """Legacy shim — real isolation now lives in ProcessExecutor."""

    def __init__(self, max_memory_mb: int = 512, max_cpu_sec: float = 30.0):
        self._executor = ProcessExecutor()

    async def run(self, preset: str, args: dict, handler=None) -> dict:
        from kernel.mcp.protocol.adapter import InternalToolAdapter
        from kernel.security.execution_policy import ExecutionPolicy
        tool = InternalToolAdapter.adapt(
            name=preset,
            description="legacy",
            handler=handler,
            capabilities=set(),
            policy=ExecutionPolicy(),
            timeout=60.0,
        )
        return await self._executor.run(tool, args)
