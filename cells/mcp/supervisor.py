"""cells/mcp/supervisor.py — Production-grade MCP supervisor with health checks."""
from __future__ import annotations
import time
import asyncio
from typing import Dict
from collections import defaultdict


class MCPSupervisor:
    """
    Background daemon that monitors tool health, crashed workers,
    resource abuse, and hung executions.
    """

    def __init__(self, heartbeat_timeout: float = 30.0):
        self.heartbeat_timeout = heartbeat_timeout
        self._beats: Dict[str, float] = {}
        self._dead: set = set()
        self._metrics = defaultdict(lambda: {"success": 0, "fail": 0, "crashes": 0, "timeouts": 0})
        self._running = False
        self._task = None

    def heartbeat(self, preset: str):
        self._beats[preset] = time.time()

    def record(self, preset: str, status: str):
        if status == "ok":
            self._metrics[preset]["success"] += 1
        elif status == "killed":
            self._metrics[preset]["timeouts"] += 1
        elif status == "error":
            self._metrics[preset]["fail"] += 1
        else:
            self._metrics[preset]["crashes"] += 1

    def check(self) -> Dict[str, str]:
        now = time.time()
        status = {}
        for preset, last in self._beats.items():
            if now - last > self.heartbeat_timeout:
                status[preset] = "dead"
                self._dead.add(preset)
            else:
                status[preset] = "alive"
        return status

    def summary(self) -> dict:
        return {
            "heartbeats": dict(self._beats),
            "dead": sorted(self._dead),
            "metrics": dict(self._metrics),
        }

    async def _loop(self):
        while self._running:
            self.check()
            await asyncio.sleep(10)

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def shutdown(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._beats.clear()
        self._dead.clear()
