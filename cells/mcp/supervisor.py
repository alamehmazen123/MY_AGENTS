"""
cells/mcp/supervisor.py — Watchdog, Heartbeat, Regeneration
"""
import time
from typing import Dict


class MCPSupervisor:
    """Supervises MCP health via heartbeat."""
    
    def __init__(self, heartbeat_timeout: float = 10.0):
        self.heartbeat_timeout = heartbeat_timeout
        self._beats: Dict[str, float] = {}
        self._dead: set = set()
    
    def heartbeat(self, preset: str):
        self._beats[preset] = time.time()
    
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
    
    def regenerate(self, preset: str):
        self._dead.discard(preset)
        self._beats[preset] = time.time()
    
    async def shutdown(self):
        self._beats.clear()
        self._dead.clear()
