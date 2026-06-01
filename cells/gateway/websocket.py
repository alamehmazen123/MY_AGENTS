"""
cells/gateway/websocket.py — Socket.io, Rooms, Backpressure
"""
from __future__ import annotations
from typing import Dict, Any
import socketio
from kernel.config import settings
from kernel.observability import recorder, generate_trace_id, set_trace_id, clear_trace_id


class WSServer:
    """Socket.io server with room management."""
    
    def __init__(self):
        self.sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
        self.app = socketio.ASGIApp(self.sio)
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.sio.event
        async def connect(sid, environ):
            recorder.record_timeline("WebSocket", "connect")
            await self.sio.enter_room(sid, "global")
        
        @self.sio.event
        async def disconnect(sid):
            recorder.record_timeline("WebSocket", "disconnect")
        
        @self.sio.on("prompt")
        async def on_prompt(sid, data):
            trace_id = generate_trace_id()
            set_trace_id(trace_id)
            recorder.begin_request(trace_id)
            recorder.record_timeline("WebSocket", "prompt_received")
            await self.sio.emit("ack", {"status": "queued", "trace_id": trace_id}, room=sid)
            recorder.end_request(trace_id)
            clear_trace_id()
    
    async def start(self):
        import asyncio
        # In production, mount alongside REST or run separate port
        pass
    
    async def stop(self):
        pass
    
    async def broadcast(self, event: str, data: Dict[str, Any]):
        await self.sio.emit(event, data, room="global")
