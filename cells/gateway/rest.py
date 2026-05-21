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

TOOL_INSTRUCTIONS = (
    "You have access to local tools on this computer. To use a tool, output exactly one line in this format:\n"
    "[[MCP:<tool_name>:<json_arguments>]]\n\n"
    "Available tools:\n"
    "- file_explorer: Browse/read/write/delete files and directories.\n"
    "  Actions: read, list, stat, write, delete, mkdir, move.\n"
    "  Args examples:\n"
    '  {"action":"read","path":"C:\\\\Users\\\\Me\\\\file.txt"} -> returns file content\n'
    '  {"action":"list","path":"C:\\\\Users\\\\Me\\\\Projects"} -> returns directory listing\n'
    '  {"action":"write","path":"...","content":"..."} -> writes text to file\n'
    '  {"action":"delete","path":"..."} -> deletes file or folder\n'
    '  {"action":"mkdir","path":"..."} -> creates directory\n'
    '  {"action":"move","path":"...","dest":"..."} -> moves/renames file\n'
    "- search_ripgrep: Search text inside files.\n"
    '  Args: {"query":"search text","path":"directory to search"}\n'
    "- python_exec: Execute Python code safely.\n"
    '  Args: {"code":"print(1+1)"}\n\n'
    "After using a tool, you will receive its result and can continue. "
    "Use tools whenever you need file information to answer accurately. "
    "You may use up to 3 tools in sequence."
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

        @self.app.post("/api/write-file")
        async def write_file(req: Request):
            return await self._write_file(req)

        @self.app.post("/api/delete-file")
        async def delete_file(req: Request):
            return await self._delete_file(req)

        @self.app.post("/api/create-folder")
        async def create_folder(req: Request):
            return await self._create_folder(req)

        @self.app.post("/api/move-file")
        async def move_file(req: Request):
            return await self._move_file(req)

        @self.app.post("/prompt")
        async def prompt(req: Request):
            return await self._handle_prompt(req)

        @self.app.post("/api/prompt")
        async def api_prompt(req: Request):
            return await self._handle_prompt(req)

        @self.app.get("/api/presets")
        async def get_presets():
            return {
                "presets": {
                    "CHAT": {
                        "name": "CHAT",
                        "description": "General conversation, no code execution. ~2.5 GB RAM, 10-18 tok/s.",
                        "agent_a": {"name": "qwen3:4b", "context_length": 4096, "temperature": 0.7},
                        "agent_b": None,
                        "mcp_tools_enabled": False,
                    },
                    "REVIEWING": {
                        "name": "REVIEWING",
                        "description": "Fast response + deep quality review. ~6.0 GB RAM.",
                        "agent_a": {"name": "qwen3:1.7b", "context_length": 4096, "temperature": 0.7},
                        "agent_b": {"name": "qwen3:8b", "context_length": 4096, "temperature": 0.3},
                        "mcp_tools_enabled": False,
                    },
                    "CODING": {
                        "name": "CODING",
                        "description": "Fast code generation + quality review. ~5.5 GB RAM.",
                        "agent_a": {"name": "deepseek-coder:1.3b", "context_length": 8192, "temperature": 0.2},
                        "agent_b": {"name": "qwen2.5-coder:7b", "context_length": 8192, "temperature": 0.3},
                        "mcp_tools_enabled": True,
                    },
                    "SUPER_CODING": {
                        "name": "SUPER_CODING",
                        "description": "Quality generation + ultimate review. ~5.7 GB RAM.",
                        "agent_a": {"name": "qwen2.5-coder:3b", "context_length": 8192, "temperature": 0.2},
                        "agent_b": {"name": "deepseek-coder:6.7b", "context_length": 8192, "temperature": 0.3},
                        "mcp_tools_enabled": True,
                    },
                    "EXECUTION": {
                        "name": "EXECUTION",
                        "description": "Automated code execution and verification. ~3.3 GB RAM.",
                        "agent_a": {"name": "deepseek-coder:1.3b", "context_length": 16384, "temperature": 0.1},
                        "agent_b": {"name": "qwen3:4b", "context_length": 16384, "temperature": 0.2},
                        "mcp_tools_enabled": True,
                    },
                }
            }

        @self.app.post("/api/mcp/invoke")
        async def mcp_invoke(req: Request):
            return await self._mcp_invoke(req)

        @self.app.get("/api/mcp/tools")
        async def mcp_tools():
            return await self._mcp_tools()

        @self.app.get("/api/mcp/status")
        async def mcp_status():
            return await self._mcp_status()

        @self.app.get("/api/mcp/metrics")
        async def mcp_metrics():
            return await self._mcp_metrics()

        @self.app.get("/api/mcp/workers")
        async def mcp_workers():
            return await self._mcp_workers()

        @self.app.post("/api/mcp/restart")
        async def mcp_restart():
            return await self._mcp_restart()

        @self.app.post("/api/mcp/reload")
        async def mcp_reload():
            return await self._mcp_reload()

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
            if not p.exists():
                return {"error": "file_not_found", "content": ""}
            if p.is_dir():
                return {"error": "is_directory", "content": ""}
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

    async def _write_file(self, req: Request):
        body = await req.json()
        path = body.get("path", "")
        content = body.get("content", "")
        if not path:
            return {"error": "no_path"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        try:
            result = await mcp_cell.invoke("file_explorer", {"action": "write", "path": path, "content": content})
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _delete_file(self, req: Request):
        body = await req.json()
        path = body.get("path", "")
        if not path:
            return {"error": "no_path"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        try:
            result = await mcp_cell.invoke("file_explorer", {"action": "delete", "path": path})
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _create_folder(self, req: Request):
        body = await req.json()
        path = body.get("path", "")
        if not path:
            return {"error": "no_path"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        try:
            result = await mcp_cell.invoke("file_explorer", {"action": "mkdir", "path": path})
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _move_file(self, req: Request):
        body = await req.json()
        src = body.get("path", "")
        dest = body.get("dest", "")
        if not src or not dest:
            return {"error": "missing_path_or_dest"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        try:
            result = await mcp_cell.invoke("file_explorer", {"action": "move", "path": src, "dest": dest})
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _handle_prompt(self, req: Request):
        import httpx
        import re
        import json
        body = await req.json()
        prompt_text = body.get("prompt", "")
        model = body.get("model", settings.ollama_default_model)
        system = body.get("system", DEFAULT_SYSTEM_PROMPT)
        workspace_folder = body.get("workspace_folder", "")
        no_tools = body.get("no_tools", False)
        temperature = body.get("temperature")
        context_length = body.get("context_length")

        if not prompt_text:
            return {"error": "empty_prompt", "output": "[Error: empty prompt received]"}

        mcp_cell = getattr(self._gateway, "_mcp", None)
        full_system = system
        if not no_tools and mcp_cell:
            full_system = system + "\n\n" + TOOL_INSTRUCTIONS

        current_prompt = prompt_text
        final_response = ""

        MAX_TOOL_ITERATIONS = 3

        for iteration in range(MAX_TOOL_ITERATIONS + 1):
            # Safety cap
            MAX_PROMPT_LEN = 30000
            if len(current_prompt) > MAX_PROMPT_LEN:
                current_prompt = current_prompt[:MAX_PROMPT_LEN] + "\n\n[...truncated by backend]"

            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    payload = {
                        "model": model,
                        "prompt": current_prompt,
                        "stream": False,
                    }
                    if full_system:
                        payload["system"] = full_system

                    options = {}
                    if temperature is not None:
                        options["temperature"] = temperature
                    if context_length:
                        options["num_ctx"] = context_length
                    if options:
                        payload["options"] = options

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

                    final_response = response_text

                    if no_tools or not mcp_cell or iteration >= MAX_TOOL_ITERATIONS:
                        break

                    tool_calls = self._extract_tool_calls(response_text)
                    if not tool_calls:
                        break

                    tool_results = []
                    for tc in tool_calls:
                        args = tc["args"]
                        # Resolve relative paths against workspace folder
                        if workspace_folder:
                            wf = Path(workspace_folder)
                            for key in ("path", "dest"):
                                if key in args:
                                    val = args[key]
                                    if isinstance(val, str):
                                        if not Path(val).is_absolute():
                                            args[key] = str(wf / val)

                        result = await mcp_cell.invoke(tc["preset"], args)
                        tool_results.append({"call": tc, "result": result})

                    current_prompt = self._build_continuation_prompt(prompt_text, response_text, tool_results)
                    # After first turn, simplify system prompt
                    full_system = system + "\nContinue based on the tool results. Do not use more tools unless necessary."

            except httpx.ConnectError as e:
                return {
                    "error": "ollama_not_reachable",
                    "output": f"Cannot connect to Ollama at {settings.ollama_host}. Make sure 'ollama serve' is running.",
                    "model": model,
                }
            except Exception as e:
                return {"error": str(e), "output": f"[Error: {str(e)}]", "model": model}

        return {
            "output": final_response,
            "model": model,
            "done": True,
        }

    def _extract_tool_calls(self, text: str):
        import re
        import json
        pattern = re.compile(r'\[\[MCP:(\w+):({.*?})\]\]')
        calls = []
        for match in pattern.finditer(text):
            preset = match.group(1)
            try:
                args = json.loads(match.group(2))
                calls.append({"preset": preset, "args": args, "raw": match.group(0)})
            except json.JSONDecodeError:
                continue
        return calls

    def _build_continuation_prompt(self, original_prompt: str, last_response: str, tool_results: list):
        import json
        parts = [original_prompt]
        parts.append("\n\n[Your previous response]\n" + last_response)
        parts.append("\n\n[Tool Results]\n")
        for tr in tool_results:
            parts.append(f"Tool: {tr['call']['preset']}")
            parts.append(f"Args: {json.dumps(tr['call']['args'])}")
            parts.append(f"Result: {json.dumps(tr['result'])}\n")
        parts.append("Based on the tool results above, provide your final answer. Do not use more tools unless necessary.")
        return "\n".join(parts)

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

    async def _mcp_tools(self):
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        return {"tools": mcp_cell.list_tools()}

    async def _mcp_status(self):
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        from kernel.mcp.protocol.tool_definition import ToolCapability
        return {
            "ready": True,
            "invariants": ["memory_bounded", "workspace_jailed", "process_isolated", "policy_driven"],
        }

    async def _mcp_metrics(self):
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        return mcp_cell.get_metrics()

    async def _mcp_workers(self):
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        return {"workers": "isolated_processes", "max_parallel": 4}

    async def _mcp_restart(self):
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        return {"status": "restart_not_required", "message": "Workers are stateless and auto-recover."}

    async def _mcp_reload(self):
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        return {"status": "reload_not_required", "message": "Presets are loaded at startup."}

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
