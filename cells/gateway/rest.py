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


DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI coding assistant. Answer precisely and accurately. "
    "Only respond with relevant information. If you don't know something, say so. "
    "Never hallucinate features, APIs, or technologies that don't exist."
)

REVIEW_SYSTEM_PROMPT = (
    "You are a senior code reviewer. Review the other agent's response carefully. "
    "Point out bugs, errors, or hallucinations. Provide a corrected, improved answer. "
    "Be concise but thorough. Never repeat raw JSON or error dumps."
)


class RESTServer:
    """FastAPI REST server."""

    def __init__(self, gateway=None):
        self.app = FastAPI(title="my_agents PRIS", version="12.0")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._gateway = gateway
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

        @self.app.get("/api/models")
        async def list_models():
            return await self._list_ollama_models()

        @self.app.post("/api/read-file")
        async def read_file(req: Request):
            return await self._read_file(req)

        @self.app.post("/api/list-folder")
        async def list_folder(req: Request):
            return await self._list_folder(req)

        @self.app.post("/prompt")
        async def prompt(req: Request):
            return await self._handle_prompt(req)

        @self.app.post("/api/prompt")
        async def api_prompt(req: Request):
            return await self._handle_prompt(req)

        @self.app.post("/api/mcp/invoke")
        async def mcp_invoke(req: Request):
            return await self._mcp_invoke(req)

    async def _list_ollama_models(self):
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(f"{settings.ollama_host}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", m.get("model", "")) for m in data.get("models", [])]
                    return {"models": models}
                return {"models": [], "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"models": [], "error": str(e)}

    async def _read_file(self, req: Request):
        body = await req.json()
        file_path = body.get("path", "")
        if not file_path:
            return {"error": "no_path", "content": ""}
        try:
            p = Path(file_path).expanduser().resolve()
            workspace = settings.workspace_root.expanduser().resolve()
            # Security: allow reading within workspace or common user dirs
            allowed = (
                str(p).startswith(str(workspace))
                or str(p).startswith(str(Path.home()))
            )
            if not allowed:
                return {"error": "path_not_allowed", "content": ""}
            if not p.exists():
                return {"error": "file_not_found", "content": ""}
            if p.is_dir():
                return {"error": "is_directory", "content": ""}
            # Limit file size to ~2MB to avoid context overflow
            MAX_SIZE = 2 * 1024 * 1024
            if p.stat().st_size > MAX_SIZE:
                return {
                    "error": "file_too_large",
                    "content": f"[File too large: {p.name} ({p.stat().st_size} bytes)]",
                }
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"content": content, "path": str(p), "name": p.name}
        except Exception as e:
            return {"error": str(e), "content": ""}

    async def _list_folder(self, req: Request):
        body = await req.json()
        folder_path = body.get("path", "")
        if not folder_path:
            return {"error": "no_path", "items": []}
        try:
            p = Path(folder_path).expanduser().resolve()
            workspace = settings.workspace_root.expanduser().resolve()
            allowed = (
                str(p).startswith(str(workspace))
                or str(p).startswith(str(Path.home()))
            )
            if not allowed:
                return {"error": "path_not_allowed", "items": []}
            if not p.exists() or not p.is_dir():
                return {"error": "not_a_directory", "items": []}
            items = []
            for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                items.append({
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                })
            return {"items": items, "path": str(p)}
        except Exception as e:
            return {"error": str(e), "items": []}

    async def _handle_prompt(self, req: Request):
        import httpx
        import re
        body = await req.json()
        prompt_text = body.get("prompt", "")
        model = body.get("model", settings.ollama_default_model)
        system = body.get("system", DEFAULT_SYSTEM_PROMPT)
        context_files = body.get("context_files", [])

        if not prompt_text:
            return {"error": "empty_prompt", "output": "[Error: empty prompt received]"}

        # ── Auto-read referenced files via MCP ──
        file_context = []
        mcp_cell = getattr(self._gateway, "_mcp", None)

        # 1. Explicit context_files from frontend
        for fpath in context_files:
            if mcp_cell:
                result = await mcp_cell.invoke("file_explorer", {"action": "read", "path": fpath})
                if "content" in result:
                    file_context.append(f"--- {result['name']} ---\n{result['content']}\n")

        # 2. Auto-detect file paths in prompt (e.g. src/main.py, config.json)
        if mcp_cell:
            detected_paths = re.findall(r'[\w\-./\\]+\.(py|js|ts|tsx|jsx|json|md|txt|yaml|yml|toml|html|css|java|go|rs|c|cpp|h|hpp)', prompt_text)
            for dp in detected_paths:
                # Avoid duplicates
                if dp in context_files:
                    continue
                result = await mcp_cell.invoke("file_explorer", {"action": "read", "path": dp})
                if "content" in result:
                    file_context.append(f"--- {result['name']} ---\n{result['content']}\n")

        if file_context:
            prompt_text = "[Attached Files]\n" + "\n".join(file_context) + "\n[User Prompt]\n" + prompt_text

        # Safety: cap prompt length to protect Ollama context window
        MAX_PROMPT_LEN = 30000
        if len(prompt_text) > MAX_PROMPT_LEN:
            prompt_text = prompt_text[:MAX_PROMPT_LEN] + "\n\n[...truncated by backend]"

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                payload = {
                    "model": model,
                    "prompt": prompt_text,
                    "stream": False,
                }
                if system:
                    payload["system"] = system

                res = await client.post(
                    f"{settings.ollama_host}/api/generate",
                    json=payload,
                    timeout=180,
                )
                if res.status_code != 200:
                    return {
                        "error": f"ollama_http_{res.status_code}",
                        "output": f"Ollama returned HTTP {res.status_code}: {res.text[:500]}",
                        "model": model,
                    }
                data = res.json()
                response_text = data.get("response", "").strip()
                if not response_text:
                    return {
                        "output": "[Model returned empty response — try again or check Ollama logs]",
                        "model": model,
                        "done": data.get("done", False),
                    }
                return {
                    "output": response_text,
                    "model": model,
                    "done": data.get("done", False),
                    "eval_count": data.get("eval_count", 0),
                }
        except httpx.ConnectError as e:
            return {
                "error": "ollama_not_reachable",
                "output": f"Cannot connect to Ollama at {settings.ollama_host}. Make sure 'ollama serve' is running.",
                "model": model,
            }
        except Exception as e:
            return {"error": str(e), "output": f"[Error: {str(e)}]", "model": model}

    async def _mcp_invoke(self, req: Request):
        body = await req.json()
        preset = body.get("preset", "")
        args = body.get("args", {})
        if not preset:
            return {"error": "missing_preset"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        try:
            result = await mcp_cell.invoke(preset, args)
            return result
        except Exception as e:
            return {"error": str(e)}

    def _setup_static(self):
        dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
        index_html = dist_dir / "index.html"

        if index_html.exists():
            self.app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

            @self.app.get("/")
            async def root():
                return FileResponse(str(index_html))

            @self.app.get("/{full_path:path}")
            async def spa_fallback(full_path: str):
                if full_path.startswith(("health", "invariants", "prompt", "api/", "assets/")):
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
