"""kernel/mcp/runtime/process_executor.py — Real process isolation for MCP tools."""
from __future__ import annotations
import asyncio
from typing import Any
from kernel.security.resource_limits import ResourceLimits
from kernel.mcp.protocol.tool_definition import ToolDefinition
from .worker_process import run_in_worker


class ProcessExecutor:
    """
    Executes a tool in a dedicated worker process.
    Enforces timeout, resource limits, and crash containment.
    """

    def __init__(self):
        self._metrics = {"invocations": 0, "timeouts": 0, "crashes": 0}

    async def run(self, tool: ToolDefinition, args: dict) -> dict:
        limits = tool.policy.limits if tool.policy else ResourceLimits()
        timeout = tool.timeout

        task_json = {"preset": tool.name, "args": args}
        limits_dict = {
            "memory_mb": limits.memory_mb,
            "cpu_seconds": limits.cpu_seconds,
            "open_files": limits.open_files,
            "timeout": limits.timeout,
        }

        loop = asyncio.get_running_loop()
        self._metrics["invocations"] += 1

        raw = await loop.run_in_executor(
            None, run_in_worker, task_json, limits_dict, timeout
        )

        if raw["status"] == "killed":
            if raw["error_message"] == "execution_timeout":
                self._metrics["timeouts"] += 1
            else:
                self._metrics["crashes"] += 1
            return {
                "error": raw["error_message"],
                "preset": tool.name,
                "sandboxed": True,
                "status": "killed",
            }

        if raw["status"] == "error":
            self._metrics["crashes"] += 1
            return {
                "error": raw["error_message"],
                "preset": tool.name,
                "sandboxed": True,
                "status": "error",
            }

        result = raw["data"]
        result["preset"] = tool.name
        result["sandboxed"] = True
        result["status"] = "ok"
        return result

    def metrics(self) -> dict:
        return dict(self._metrics)
