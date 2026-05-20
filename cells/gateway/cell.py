"""
cells/gateway/cell.py — GatewayCell
REST + WebSocket integration.
"""
from __future__ import annotations
from cells.base import BaseCell
from kernel.events import bus
from kernel.config import settings


class GatewayCell(BaseCell):
    """
    Gateway layer: external API surface.
    """
    
    def __init__(self):
        super().__init__("gateway")
        self._invariants = ["single_runtime", "memory_bounded"]
        self._rest = None
        self._websocket = None
        self._protocol = None
        self._upload = None
        self._server = None
    
    async def _on_init(self):
        from cells.gateway.rest import RESTServer
        from cells.gateway.websocket import WSServer
        from cells.gateway.protocol import Protocol
        from cells.gateway.upload import UploadHandler
        self._rest = RESTServer()
        self._websocket = WSServer()
        self._protocol = Protocol()
        self._upload = UploadHandler()
        await bus.emit("cell.gateway.ready", {"ports": {"api": settings.api_port, "ws": settings.ws_port}})
    
    async def start_servers(self):
        await self._rest.start()
        await self._websocket.start()
    
    async def _on_shutdown(self):
        if self._rest:
            await self._rest.stop()
        if self._websocket:
            await self._websocket.stop()
        await bus.emit("cell.gateway.offline", {})
