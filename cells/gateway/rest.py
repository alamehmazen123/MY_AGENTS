"""
cells/gateway/rest.py — FastAPI Routes
"""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
        self._setup_static()
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
    
    def _setup_static(self):
        dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
        index_html = dist_dir / "index.html"

        if index_html.exists():
            # Serve built static files: /assets from disk, / from index.html
            self.app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

            @self.app.get("/")
            async def root():
                return FileResponse(str(index_html))

            # SPA fallback: any unmatched path returns index.html
            @self.app.get("/{full_path:path}")
            async def spa_fallback(full_path: str):
                # Don't shadow API routes
                if full_path.startswith(("health", "invariants", "prompt")):
                    from fastapi.exceptions import HTTPException
                    raise HTTPException(status_code=404, detail="Not Found")
                return FileResponse(str(index_html))
        else:
            @self.app.get("/", response_class=HTMLResponse)
            async def root():
                return """<!doctype html>
<html>
<head><title>my_agents</title><meta charset="utf-8"></head>
<body style="font-family:system-ui;padding:40px;max-width:600px;margin:auto;">
<h1>my_agents PRIS v12.0</h1>
<p>✅ Backend is running.</p>
<p>⚠️ Frontend not available.</p>
<hr>
<h3>To use the web UI, choose one:</h3>
<ol>
<li><b>Dev mode (requires Node.js):</b><br>
<pre>cd frontend && npm install && npm run dev</pre>
Then open <a href="http://localhost:5173">http://localhost:5173</a>
</li>
<li><b>Static mode (requires Node.js once):</b><br>
<pre>cd frontend && npm install && npm run build</pre>
Then restart <code>python kernel/main.py</code>
</li>
</ol>
<p>Download Node.js: <a href="https://nodejs.org">https://nodejs.org</a></p>
</body>
</html>"""

    async def start(self):
        import asyncio
        config = uvicorn.Config(self.app, host="0.0.0.0", port=settings.api_port, log_level="warning")
        self._server = uvicorn.Server(config)
        asyncio.create_task(self._server.serve())
    
    async def stop(self):
        if self._server:
            self._server.should_exit = True
