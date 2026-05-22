"""kernel/mcp/runtime/execution_pool.py — Parallel execution with limits."""
from __future__ import annotations
import asyncio
from typing import Any
from kernel.mcp.protocol.tool_definition import ToolDefinition
from .process_executor import ProcessExecutor


class ExecutionPool:
    """Execute up to N tools in parallel."""

    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._executor = ProcessExecutor()

    async def execute(self, tool: ToolDefinition, args: dict, workspace: str | None = None) -> dict:
        async with self._semaphore:
            return await self._executor.run(tool, args, workspace=workspace)

    async def execute_many(self, tasks: list[tuple[ToolDefinition, dict]]) -> list[dict]:
        return await asyncio.gather(
            *[self.execute(tool, args) for tool, args in tasks]
        )

    def metrics(self) -> dict:
        return self._executor.metrics()
