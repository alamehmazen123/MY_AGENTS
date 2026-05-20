"""
cells/gateway/rest.py — FastAPI Routes
"""
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from kernel.config import settings


class RESTServer:
    """FastAPI REST server."""
    
    def __init__(self):
        self.app = FastAPI(title="my_agents PRIS", version="12.0")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._setup_routes()
        self._server = None
    
    def _setup_routes(self):
        @self.app.get("/health")
        async def health():
            return {"status": "ok", "version": "12.0"}
        
        @self.app.get("/invariants")
        async def invariants():
            from kernel.lattice_verifier import CORE_INVARIANTS
            return {"invariants": CORE_INVARIANTS}
        
        @self.app.post("/prompt")
        async def prompt(req: Request):
            body = await req.json()
            return {"task_id": "simulated", "status": "queued"}
    
    async def start(self):
        import asyncio
        config = uvicorn.Config(self.app, host="0.0.0.0", port=settings.api_port, log_level="warning")
        self._server = uvicorn.Server(config)
        asyncio.create_task(self._server.serve())
    
    async def stop(self):
        if self._server:
            self._server.should_exit = True
