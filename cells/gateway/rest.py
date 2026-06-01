"""
cells/gateway/rest.py — FastAPI Routes
"""
from __future__ import annotations
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from kernel.config import settings
from kernel.observability import (
    generate_trace_id,
    get_trace_id,
    set_trace_id,
    clear_trace_id,
    recorder,
)
import logging

# Forensic tool-trace logger
logger = logging.getLogger("tool_trace")
if not logger.handlers:
    _th = logging.StreamHandler()
    _th.setFormatter(logging.Formatter("%(asctime)s [TOOL_TRACE] %(message)s"))
    logger.addHandler(_th)
    logger.setLevel(logging.INFO)


CORE_INSTRUCTIONS_FILE = Path(__file__).resolve().parent.parent.parent / "core_instructions.md"
_CORE_CACHE: dict = {"mtime": None, "text": ""}


def _load_core_instructions() -> str:
    """Load the project-wide core instructions (core_instructions.md), cached and
    auto-reloaded when the file changes. Applied to every agent and preset."""
    try:
        if not CORE_INSTRUCTIONS_FILE.exists():
            return ""
        mtime = CORE_INSTRUCTIONS_FILE.stat().st_mtime
        if _CORE_CACHE["mtime"] != mtime:
            _CORE_CACHE["text"] = CORE_INSTRUCTIONS_FILE.read_text(encoding="utf-8", errors="replace").strip()
            _CORE_CACHE["mtime"] = mtime
        return _CORE_CACHE["text"]
    except Exception:
        return ""


DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI coding assistant. Answer precisely and accurately. "
    "Only respond with relevant information. If you don't know something, say so. "
    "Never hallucinate features, APIs, or technologies that don't exist. "
    "Never invent data such as file names, news headlines, IP addresses, or numbers — "
    "only state what you were actually given."
)

# Used INSTEAD of the preset's system prompt once tools have already executed.
# It stops models (especially coding-tuned ones) from writing code or step-by-step
# plans and forces them to report the real tool output.
SYNTHESIS_SYSTEM_PROMPT = (
    "You are a precise assistant reporting the results of tools that have ALREADY been run. "
    "The TOOL EXECUTION RESULTS below are real, actual output from the user's machine.\n"
    "RULES:\n"
    "1. Report the actual results directly and concisely. Answer each part of the user's request.\n"
    "2. Do NOT write code. Do NOT describe steps to perform. Do NOT explain how tools work. "
    "The work is already done — just give the answer.\n"
    "3. NEVER invent or guess data. Use ONLY the values present in the tool results. "
    "If a result is empty, errored, or a value was not found, say so plainly "
    "(e.g. 'CNN did not return a headline').\n"
    "4. When asked for files of a specific type, list ONLY the files that actually match that type."
)

REVIEW_SYSTEM_PROMPT = (
    "You are a senior code reviewer. Review the other agent's response carefully. "
    "Point out bugs, errors, or hallucinations. Provide a corrected, improved answer. "
    "Be concise but thorough. Never repeat raw JSON or error dumps."
)

TOOL_INSTRUCTIONS = (
    "You are an agent with DIRECT ACCESS to local tools. "
    "When the user asks for file listings, file contents, directory structure, code search, or file operations, "
    "you MUST use the relevant tool IMMEDIATELY. "
    "NEVER explain how to use tools. NEVER describe what you would do. "
    "ALWAYS execute the tool and return the actual result.\n\n"
    "To use a tool, output EXACTLY one line in this format (no markdown, no backticks, no explanation):\n"
    "[[MCP:<tool_name>:<json_arguments>]]\n\n"
    "Available tools:\n"
    "- file_explorer: Browse/read/write/delete files and directories.\n"
    "  Actions: read, list, stat, write, delete, mkdir, move.\n"
    "  Examples:\n"
    '  [[MCP:file_explorer:{"action":"list","path":"."}]]\n'
    '  [[MCP:file_explorer:{"action":"read","path":"main.py"}]]\n'
    '  [[MCP:file_explorer:{"action":"write","path":"out.txt","content":"hello"}]]\n'
    "- search_ripgrep: Search text inside files.\n"
    '  [[MCP:search_ripgrep:{"query":"def main","path":"."}]]\n'
    "- python_exec: Execute Python code safely.\n"
    '  [[MCP:python_exec:{"code":"print(1+1)"}]]\n'
    "- web_fetch: Fetch a web page and read its title/text (use for news sites, docs, any URL).\n"
    '  [[MCP:web_fetch:{"url":"https://www.cnn.com"}]]\n'
    "- network_info: Get this machine's local and public IP address.\n"
    '  [[MCP:network_info:{}]]\n\n'
    "RULES:\n"
    "1. To read a file's contents or to create/modify files, you MUST output a tool call line. "
    "If a COMPLETE LIST OF FILES is already provided in the context, answer listing/counting "
    "questions directly from it without a tool call.\n"
    "2. Do NOT wrap the line in markdown code blocks.\n"
    "3. Do NOT add explanations before or after the tool call.\n"
    "4. After receiving the tool result, answer using the actual data.\n"
    "5. You may chain up to 3 tools in sequence.\n"
    "6. ALL paths are RELATIVE to the user's workspace folder. Use \".\" for the "
    "workspace root (e.g. to list everything). NEVER use absolute drive paths like "
    "\"C:\\\\\" or \"/\" — they are outside the workspace and will be rejected."
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
        # Observability middleware — injects trace_id into every request
        @self.app.middleware("http")
        async def observability_middleware(request: Request, call_next):
            if not settings.observability_enabled:
                return await call_next(request)

            trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
            set_trace_id(trace_id)
            recorder.begin_request(trace_id)
            start = time.time()
            try:
                response = await call_next(request)
                response.headers["X-Trace-ID"] = trace_id
                return response
            except Exception as e:
                recorder.record_failure(
                    "http_middleware",
                    e,
                    {"path": request.url.path, "method": request.method},
                )
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                recorder.record_timeline(
                    "Gateway", f"{request.method} {request.url.path}", duration_ms
                )
                recorder.record_performance("gateway", duration_ms)
                recorder.end_request(trace_id)
                clear_trace_id()

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

        @self.app.post("/api/pick-folder")
        async def pick_folder():
            return await self._pick_folder()

        @self.app.post("/api/upload-paste")
        async def upload_paste(req: Request):
            return await self._upload_paste(req)

        @self.app.get("/api/core-instructions")
        async def core_instructions():
            return {"instructions": _load_core_instructions(), "applied": True}

        @self.app.get("/api/ollama-ps")
        async def ollama_ps():
            return await self._ollama_ps()

        @self.app.post("/api/unload-model")
        async def unload_model(req: Request):
            return await self._unload_model(req)

        @self.app.post("/api/execute-plan")
        async def execute_plan(req: Request):
            return await self._execute_plan(req)

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
                        "agent_b": {"name": "qwen2.5-coder:3b", "context_length": 8192, "temperature": 0.3},
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

        # ---- Observability Dashboard Routes ----
        @self.app.get("/api/observability/metrics")
        async def observability_metrics():
            from kernel.observability.dashboard import get_dashboard_metrics
            return get_dashboard_metrics()

        @self.app.get("/api/observability/traces")
        async def observability_traces(n: int = 50):
            from kernel.observability.dashboard import get_recent_traces
            return {"traces": get_recent_traces(n)}

        @self.app.get("/api/observability/failures")
        async def observability_failures(n: int = 50):
            from kernel.observability.dashboard import get_recent_failures
            return {"failures": get_recent_failures(n)}

        @self.app.get("/api/observability/logs")
        async def observability_logs_list():
            from kernel.observability.logger import list_log_files
            return {"logs": list_log_files()}

        @self.app.get("/api/observability/logs/{name}")
        async def observability_log_tail(name: str, lines: int = 100):
            from kernel.observability.logger import tail_log_file
            return {"name": name, "lines": tail_log_file(name, lines)}

        @self.app.get("/api/observability/trace-id")
        async def observability_trace_id():
            from kernel.observability.trace_context import get_trace_id
            return {"trace_id": get_trace_id() or "NO_TRACE"}

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

    async def _upload_paste(self, req: Request):
        """Save a pasted blob (image/file) from the browser clipboard to disk
        and return its absolute path so agents can reference it via tools."""
        import base64
        import re
        import time
        try:
            body = await req.json()
        except Exception as e:
            return {"error": f"bad_json: {e}"}
        name = (body.get("name") or "").strip() or f"pasted_{int(time.time())}.bin"
        mime = body.get("mime") or "application/octet-stream"
        data_b64 = body.get("data_base64") or ""
        if not data_b64:
            return {"error": "missing_data_base64"}
        # Sanitise filename — keep extension, strip path separators.
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[-120:] or f"pasted_{int(time.time())}"
        # If no extension and we know the mime, add a sensible one.
        if "." not in safe:
            ext = {
                "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
                "image/webp": ".webp", "image/bmp": ".bmp",
                "text/plain": ".txt", "application/pdf": ".pdf",
            }.get(mime, ".bin")
            safe = f"{safe}{ext}"
        try:
            raw = base64.b64decode(data_b64)
        except Exception as e:
            return {"error": f"bad_base64: {e}"}
        out_dir = settings.data_dir / "pasted"
        out_dir.mkdir(parents=True, exist_ok=True)
        # Add a short timestamp prefix so repeated pastes don't overwrite each other.
        final_name = f"{int(time.time())}_{safe}"
        out_path = out_dir / final_name
        try:
            out_path.write_bytes(raw)
        except Exception as e:
            return {"error": f"write_failed: {e}"}
        return {
            "name": final_name,
            "path": str(out_path),
            "size": len(raw),
            "mime": mime,
        }

    def _resolve_workspace(self, folder: str) -> str:
        """Normalize a user-supplied workspace folder to an absolute directory.
        Accepts absolute paths, paths relative to home, and bare well-known
        names like 'Desktop'/'Documents'/'Downloads'. Returns '' if unresolvable."""
        if not folder:
            return ""
        try:
            p = Path(folder).expanduser()
            if p.is_dir():
                return str(p.resolve())
            # Bare/relative name → try under the user's home directory.
            candidate = (Path.home() / folder).expanduser()
            if candidate.is_dir():
                return str(candidate.resolve())
        except Exception:
            pass
        return ""

    async def _pick_folder(self):
        """Open a native OS folder-picker dialog (this runs on the user's own
        machine since the app is localhost) and return the chosen absolute path."""
        import asyncio
        import sys
        script = (
            "import tkinter as tk\n"
            "from tkinter import filedialog\n"
            "r = tk.Tk(); r.withdraw()\n"
            "try:\n"
            "    r.attributes('-topmost', True)\n"
            "except Exception:\n"
            "    pass\n"
            "p = filedialog.askdirectory(title='Select workspace folder')\n"
            "print(p or '')\n"
            "r.destroy()\n"
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=300)
            path = out.decode("utf-8", errors="replace").strip()
            if not path:
                return {"path": "", "cancelled": True}
            return {"path": path}
        except asyncio.TimeoutError:
            return {"path": "", "error": "picker_timeout"}
        except Exception as e:
            return {"path": "", "error": str(e)}

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
        import time as _time
        _prompt_start = _time.time()
        recorder.record_timeline("Gateway", "received_prompt")
        body = await req.json()
        prompt_text = body.get("prompt", "")
        model = body.get("model", settings.ollama_default_model)
        system = body.get("system", DEFAULT_SYSTEM_PROMPT)
        workspace_folder = self._resolve_workspace(body.get("workspace_folder", ""))
        # If the user didn't pick a folder, try to infer one from the words
        # ("my desktop", "downloads", ...) so file requests still target the right place.
        if not workspace_folder:
            workspace_folder = self._infer_workspace_from_prompt(prompt_text)
            if workspace_folder:
                logger.info("[TOOL_TRACE] inferred_workspace=%s", workspace_folder)
        no_tools = body.get("no_tools", False)
        temperature = body.get("temperature")
        context_length = body.get("context_length")
        preset_name = body.get("preset", "UNKNOWN")

        if not prompt_text:
            return {"error": "empty_prompt", "output": "[Error: empty prompt received]"}

        # Fail fast if the requested model is not installed — otherwise Ollama
        # may stall trying to resolve it, which looks like a hang to the user.
        available = (await self._list_ollama_models()).get("models", [])
        if available and model not in available:
            base = model.split(":")[0]
            if not any(m == model or m.split(":")[0] == base for m in available):
                return {
                    "error": "model_not_installed",
                    "output": (
                        f"[Error: model '{model}' is not installed in Ollama. "
                        f"Run `ollama pull {model}` or pick an installed model. "
                        f"Installed: {', '.join(available) or 'none'}]"
                    ),
                    "model": model,
                }

        mcp_cell = getattr(self._gateway, "_mcp", None)
        full_system = system
        tools_enabled = not no_tools and mcp_cell is not None
        if tools_enabled:
            full_system = system + "\n\n" + TOOL_INSTRUCTIONS

        logger.info("[TOOL_TRACE] stage=A preset=%s model=%s no_tools=%s tools_enabled=%s mcp_available=%s prompt_preview=%s",
                    preset_name, model, no_tools, tools_enabled, mcp_cell is not None, prompt_text[:200])

        current_prompt = prompt_text
        context_injected = False

        # Claude-Code-style environment awareness: when tools are on and a workspace
        # folder is set, give the agent a real listing of that folder up front so it
        # knows what exists instead of guessing paths or claiming it has no access.
        if tools_enabled and workspace_folder:
            try:
                listing = await mcp_cell.invoke(
                    "file_explorer", {"action": "list", "path": "."}, workspace=workspace_folder
                )
                items = listing.get("items") if isinstance(listing, dict) else None
                if items:
                    names = ", ".join(
                        f"{i.get('name')}{'/' if i.get('type') == 'dir' else ''}" for i in items[:300]
                    )
                    # Pre-compute facts deterministically so a weak model doesn't
                    # have to count/filter (the part small LLMs get wrong).
                    files = [i for i in items if i.get("type") != "dir"]
                    dirs = [i for i in items if i.get("type") == "dir"]
                    ext_counts: dict[str, int] = {}
                    for i in files:
                        name = i.get("name", "")
                        ext = name[name.rfind("."):].lower() if "." in name else "(no ext)"
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    counts_str = ", ".join(
                        f"{ext}={n}" for ext, n in sorted(ext_counts.items(), key=lambda kv: -kv[1])
                    )
                    # If the user named specific extensions (e.g. ".txt"), give the
                    # EXACT matching list so the model can't mistake .lnk/folders for it.
                    import re as _re
                    filtered_blocks = ""
                    for ext in dict.fromkeys(_re.findall(r'\.([a-z0-9]{1,6})\b', prompt_text.lower())):
                        matches = [i.get("name") for i in files if i.get("name", "").lower().endswith("." + ext)]
                        filtered_blocks += f"[EXACT .{ext} FILES ({len(matches)}): {', '.join(matches) if matches else 'none'}]\n"
                    current_prompt = (
                        f"[WORKSPACE: {workspace_folder}]\n"
                        f"[FACTS — workspace root: {len(files)} files, {len(dirs)} folders]\n"
                        f"[FILE COUNTS BY EXTENSION: {counts_str}]\n"
                        f"{filtered_blocks}"
                        f"[COMPLETE FILE/FOLDER LIST: {names}]\n"
                        "The FACTS and lists above are computed directly from the file system and "
                        "are exact. When asked for files of a specific type, use the matching "
                        "'EXACT .<ext> FILES' list verbatim — do NOT include folders or other file "
                        "types. For counts, use the numbers above. Do NOT call a tool or recount.\n\n"
                        f"{prompt_text}"
                    )
                    context_injected = True
            except Exception as e:
                logger.info("[TOOL_TRACE] workspace_context_failed=%s", str(e))

        final_response = ""
        any_tool_executed = False
        all_tool_results: list = []  # real tool output, also returned for Agent-B

        # Run any clearly-intended tools UP FRONT (deterministically, from the
        # prompt) and feed the results in, so the model answers in a single pass
        # instead of emitting tool calls across several slow generations.
        if tools_enabled:
            forced = self._force_tool_detection(prompt_text, context_injected)
            if forced:
                pre_results = []
                for tc in forced:
                    args = dict(tc["args"])
                    if workspace_folder:
                        wf = Path(workspace_folder)
                        for key in ("path", "dest"):
                            if isinstance(args.get(key), str) and not Path(args[key]).is_absolute():
                                args[key] = str(wf / args[key])
                    logger.info("[TOOL_TRACE] stage=PRE preset=%s args=%s", tc["preset"], json.dumps(args))
                    result = await mcp_cell.invoke(tc["preset"], args, workspace=workspace_folder or None)
                    pre_results.append({"call": tc, "result": result})
                    any_tool_executed = True
                all_tool_results.extend(pre_results)
                current_prompt = self._build_continuation_prompt(current_prompt, "(no attempt yet)", pre_results)
                # Tools already ran — REPLACE the preset system prompt entirely with
                # the synthesis prompt so coding-tuned models report results instead
                # of writing code/plans, and don't fabricate missing values.
                full_system = SYNTHESIS_SYSTEM_PROMPT

        # The base request used when rebuilding continuation prompts. Includes the
        # injected workspace facts + any up-front tool results.
        base_prompt = current_prompt

        MAX_TOOL_ITERATIONS = 3

        try:
            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                # Safety cap
                MAX_PROMPT_LEN = 30000
                if len(current_prompt) > MAX_PROMPT_LEN:
                    current_prompt = current_prompt[:MAX_PROMPT_LEN] + "\n\n[...truncated by backend]"

                async with httpx.AsyncClient(timeout=300) as client:
                    payload = {
                        "model": model,
                        "prompt": current_prompt,
                        "stream": False,
                    }
                    # Prepend the project-wide core instructions (Karpathy
                    # guidelines) to EVERY agent/preset, on every generation.
                    core = _load_core_instructions()
                    combined_system = (core + "\n\n" + full_system).strip() if core else full_system
                    if combined_system:
                        payload["system"] = combined_system
                    logger.info("[TOOL_TRACE] core_applied=%s combined_system_len=%s", bool(core), len(combined_system or ""))

                    options = {}
                    if temperature is not None:
                        options["temperature"] = temperature
                    if context_length:
                        options["num_ctx"] = context_length
                    # Cap output length. Without this, small models can ramble until
                    # they fill the whole context window (thousands of tokens), which
                    # takes minutes and trips the request timeout. Override via body.
                    options["num_predict"] = body.get("max_tokens", 2048)
                    payload["options"] = options

                    # Disable extended "thinking" for reasoning models (qwen3,
                    # deepseek-r1, gpt-oss). Their hidden chain-of-thought burns
                    # thousands of tokens and is the main cause of timeouts here.
                    low = model.lower()
                    if any(tag in low for tag in ("qwen3", "-r1", "r1:", "gpt-oss", "thinking")):
                        payload["think"] = False

                    # Keep the model resident across tool iterations to avoid
                    # reloading it from disk every round (the main source of latency).
                    # The single explicit unload happens in the finally block below,
                    # guaranteeing zero models loaded once this agent's turn ends.
                    payload["keep_alive"] = "5m"

                    logger.info("stage=B ollama_request iteration=%s prompt_len=%s system_len=%s", iteration, len(current_prompt), len(full_system or ""))
                    _ollama_start = _time.time()
                    recorder.record_timeline("Agent-A", "ollama_request")
                    recorder.record_agent_reasoning(
                        agent="Agent-A",
                        prompt_length=len(current_prompt),
                        model=model,
                        tools_detected=len(self._extract_tool_calls(current_prompt)),
                        tools_executed=0,
                        response_length=0,
                    )

                    res = await client.post(
                        f"{settings.ollama_host}/api/generate",
                        json=payload,
                        timeout=300,
                    )
                    _ollama_ms = (_time.time() - _ollama_start) * 1000
                    recorder.record_timeline("Agent-A", "ollama_completed", _ollama_ms)
                    recorder.record_performance("ollama", _ollama_ms)
                    if res.status_code != 200:
                        logger.info("stage=G ollama_error status=%s", res.status_code)
                        return {
                            "error": f"ollama_http_{res.status_code}",
                            "output": f"Ollama returned HTTP {res.status_code}: {res.text[:500]}",
                            "model": model,
                        }
                    data = res.json()
                    response_text = data.get("response", "").strip()
                    logger.info("stage=B model_response_len=%s", len(response_text))
                    if not response_text:
                        return {
                            "output": "[Model returned empty response — try again or check Ollama logs]",
                            "model": model,
                            "done": data.get("done", False),
                        }

                    final_response = response_text

                    if not tools_enabled or iteration >= MAX_TOOL_ITERATIONS:
                        break

                    tool_calls = self._extract_tool_calls(response_text)
                    logger.info("[TOOL_TRACE] stage=C extracted_tool_count=%s", len(tool_calls))

                    # PHASE 7 — Force tool execution for explicit tool requests.
                    # Only on the first turn: once tools have run, the model must
                    # answer from the results instead of looping on the same request.
                    if not tool_calls and iteration == 0 and not any_tool_executed:
                        forced = self._force_tool_detection(prompt_text, context_injected)
                        if forced:
                            logger.info("[TOOL_TRACE] stage=C_forced forced_calls=%s", json.dumps([f["preset"] for f in forced]))
                            tool_calls = forced

                    if not tool_calls:
                        logger.info("[TOOL_TRACE] stage=C_no_tools breaking_loop")
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

                        logger.info("[TOOL_TRACE] stage=D dispatching_mcp preset=%s args=%s", tc["preset"], json.dumps(args))
                        _mcp_start = _time.time()
                        result = await mcp_cell.invoke(tc["preset"], args, workspace=workspace_folder or None)
                        _mcp_ms = (_time.time() - _mcp_start) * 1000
                        _mcp_status = "SUCCESS" if (isinstance(result, dict) and not result.get("error")) else "FAILURE"
                        recorder.record_mcp_call(
                            tool=tc["preset"],
                            args=args,
                            duration_ms=_mcp_ms,
                            status=_mcp_status,
                            error=result.get("error") if isinstance(result, dict) else None,
                        )
                        recorder.record_timeline("MCP", f"tool_{tc['preset']}", _mcp_ms)
                        recorder.record_performance("mcp", _mcp_ms)
                        logger.info("[TOOL_TRACE] stage=E tool_result preset=%s result=%s", tc["preset"], json.dumps(result)[:500])
                        tool_results.append({"call": tc, "result": result})
                        any_tool_executed = True

                    all_tool_results.extend(tool_results)

                    # Fast path: if every tool succeeded, synthesize a short
                    # deterministic summary and skip another model round. This
                    # prevents big-model continuation generations from timing
                    # out (an 8B/14B model can take >5min to summarize on CPU)
                    # and gives the user immediate confirmation of the action.
                    all_ok = all(
                        isinstance(r["result"], dict) and not r["result"].get("error")
                        for r in tool_results
                    )
                    if all_ok:
                        final_response = self._summarize_tool_success(tool_results)
                        logger.info("[TOOL_TRACE] stage=F fast_path_summary len=%s", len(final_response))
                        break

                    current_prompt = self._build_continuation_prompt(base_prompt, response_text, tool_results)
                    logger.info("stage=F context_after_tool prompt_len=%s", len(current_prompt))
                    # After first turn, simplify system prompt
                    full_system = system + "\nContinue based on the tool results. Do not use more tools unless necessary."

        except httpx.ConnectError as e:
            logger.info("stage=G ollama_connect_error")
            recorder.record_failure("ollama_connect_error", e, {"model": model})
            return {
                "error": "ollama_not_reachable",
                "output": f"Cannot connect to Ollama at {settings.ollama_host}. Make sure 'ollama serve' is running.",
                "model": model,
            }
        except httpx.TimeoutException:
            logger.info("stage=G ollama_timeout")
            recorder.record_failure("ollama_timeout", None, {"model": model})
            return {
                "error": "ollama_timeout",
                "output": (
                    f"[Error: '{model}' did not respond within 300s. "
                    "It may be cold-loading a large model or generating too much. "
                    "Try a smaller model or a simpler prompt.]"
                ),
                "model": model,
            }
        except Exception as e:
            logger.info("stage=G exception=%s", str(e))
            recorder.record_failure("prompt_handler_exception", e, {"model": model})
            return {"error": str(e) or "unknown_error", "output": f"[Error: {str(e) or 'unknown error'}]", "model": model}
        finally:
            # Single unload at the end of this agent's turn — guarantees zero
            # models loaded before the next agent (B) starts, without paying the
            # reload cost on every tool iteration.
            await self._unload_model_quiet(model)
            _prompt_total_ms = (_time.time() - _prompt_start) * 1000
            recorder.record_timeline("Gateway", "response_sent", _prompt_total_ms)
            recorder.record_performance("total_request", _prompt_total_ms)

        # PHASE 11 — Hallucination prevention
        if any_tool_executed:
            logger.info("[TOOL_TRACE] stage=H final_response_tools_used=%s", any_tool_executed)
        else:
            logger.info("[TOOL_TRACE] stage=H final_response_no_tools")

        # Build a compact, ground-truth tool context to hand to Agent-B so its
        # review is checked against real data instead of being fabricated.
        tool_context = ""
        for tr in all_tool_results:
            rj = json.dumps(tr["result"])
            if len(rj) > 1500:
                rj = rj[:1500] + " …(truncated)"
            tool_context += f"- {tr['call']['preset']}({json.dumps(tr['call']['args'])}): {rj}\n"

        recorder.record_agent_reasoning(
            agent="Agent-A",
            prompt_length=len(prompt_text),
            model=model,
            tools_detected=len(self._extract_tool_calls(prompt_text)),
            tools_executed=len(all_tool_results),
            response_length=len(final_response),
        )

        _current_trace_id = get_trace_id()
        return {
            "output": final_response,
            "model": model,
            "done": True,
            "trace_id": _current_trace_id,
            "tool_context": tool_context,
            "tool_results": [
                {
                    "tool": tr["call"]["preset"],
                    "args": tr["call"].get("args", {}),
                    "result": tr["result"],
                }
                for tr in all_tool_results
            ],
        }

    async def _unload_model_quiet(self, model: str):
        """Best-effort unload of a model from Ollama (keep_alive=0). Never raises."""
        import httpx
        if not model:
            return
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(
                    f"{settings.ollama_host}/api/generate",
                    json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
                    timeout=30,
                )
        except Exception:
            pass

    def _summarize_tool_success(self, tool_results: list) -> str:
        """Build a short deterministic summary from successful tool results so
        we can short-circuit the slow follow-up model generation."""
        lines = ["**Done.**"]
        for tr in tool_results:
            preset = tr["call"]["preset"]
            args = tr["call"].get("args", {})
            res = tr["result"]
            if preset == "file_explorer":
                act = args.get("action", "")
                p = res.get("path", args.get("path", ""))
                if act == "write":
                    lines.append(f"- Wrote `{p}` ({res.get('bytes_written', '?')} bytes).")
                elif act == "read":
                    n = len(res.get("content", "") or "")
                    lines.append(f"- Read `{p}` ({n} chars).")
                elif act == "list":
                    lines.append(f"- Listed `{p}` — {len(res.get('items', []))} items.")
                elif act == "delete":
                    lines.append(f"- Deleted `{p}`.")
                elif act == "mkdir":
                    lines.append(f"- Created folder `{p}`.")
                else:
                    lines.append(f"- file_explorer/{act} on `{p}` ok.")
            elif preset == "web_fetch":
                lines.append(f"- Fetched `{res.get('url', args.get('url'))}` — {res.get('text_length', 0)} chars; {len(res.get('headlines', []))} headlines.")
            elif preset == "network_info":
                lines.append(f"- IP: local={res.get('local_ip')}, public={res.get('public_ip')}.")
            elif preset == "python_exec":
                out = (res.get("stdout") or "").strip()
                lines.append(f"- Ran Python — stdout: `{out[:120]}`" if out else "- Ran Python (no stdout).")
            elif preset == "search_ripgrep":
                lines.append(f"- Search returned {len(res.get('matches', []))} matches.")
            else:
                preview = json.dumps(res)[:160]
                lines.append(f"- `{preset}` ok — {preview}")
        return "\n".join(lines)

    def _parse_args_block(self, block: str):
        """Parse the {...} body of a [[MCP:...]] call. Tries strict JSON first,
        then Python-literal parsing (handles triple-quoted strings, single
        quotes, trailing commas — common LLM JSON mistakes)."""
        import json
        import ast
        try:
            return json.loads(block)
        except Exception:
            pass
        try:
            # ast.literal_eval accepts Python dict literals, which permit
            # \"\"\"multi-line\"\"\" content and 'single quotes' that JSON forbids.
            value = ast.literal_eval(block)
            if isinstance(value, dict):
                return value
        except Exception:
            pass
        return None

    def _extract_tool_calls(self, text: str):
        import re
        # Primary: single-line or multi-line JSON inside [[MCP:preset:{...}]]
        pattern = re.compile(r'\[\[MCP:(\w+):\s*({.*?)\s*\]\]', re.DOTALL)
        calls = []
        for match in pattern.finditer(text):
            preset = match.group(1)
            args = self._parse_args_block(match.group(2))
            if args is not None:
                calls.append({"preset": preset, "args": args, "raw": match.group(0)})
        if not calls:
            # Fallback: match inside markdown code blocks that contain [[MCP:...]]
            md_pattern = re.compile(r'```.*?\n(.*?)\n```', re.DOTALL)
            for md_match in md_pattern.finditer(text):
                inner = md_match.group(1)
                for m in re.finditer(r'\[\[MCP:(\w+):\s*({.*?)\s*\]\]', inner, re.DOTALL):
                    args = self._parse_args_block(m.group(2))
                    if args is not None:
                        calls.append({"preset": m.group(1), "args": args, "raw": m.group(0)})
        return calls

    def _infer_workspace_from_prompt(self, prompt_text: str) -> str:
        """Infer a workspace folder from natural language ('my desktop',
        'documents', 'downloads', 'home') so the user need not pick one manually."""
        low = prompt_text.lower()
        for name in ("desktop", "documents", "downloads", "pictures", "music", "videos"):
            if name in low:
                cand = Path.home() / name.capitalize()
                if cand.is_dir():
                    return str(cand)
        if "home folder" in low or "home directory" in low or "my home" in low:
            return str(Path.home())
        return ""

    def _force_tool_detection(self, prompt_text: str, context_injected: bool = False):
        """Detect tool intents in a plain-language prompt and return a LIST of
        forced tool calls. Handles multiple intents in one prompt (e.g. list files
        + fetch a website + get IP), so multi-part requests all execute."""
        import re
        lowered = prompt_text.lower()
        logger.info("[TOOL_TRACE] FORCE_CHECK prompt=%s", prompt_text[:200])

        def near(words):
            for sentence in re.split(r'[.!?\n,;]', lowered):
                if all(w in sentence for w in words):
                    return True
            return False

        calls = []

        # 1. Web fetch — explicit domain/URL, or a known site name.
        KNOWN_TLDS = ("com", "org", "net", "io", "gov", "edu", "news", "co", "ai")
        url = None
        for m in re.finditer(r'((?:https?://)?[a-z0-9][a-z0-9\-]*(?:\.[a-z0-9\-]+)+(?:/[^\s]*)?)', lowered):
            cand = m.group(1)
            host = cand.split("//")[-1].split("/")[0]
            tld = host.rsplit(".", 1)[-1]
            if tld in KNOWN_TLDS:
                url = cand
                break
        if not url:
            for site, dom in (("cnn", "cnn.com"), ("bbc", "bbc.com"), ("reuters", "reuters.com"),
                              ("wikipedia", "wikipedia.org"), ("github", "github.com"), ("hacker news", "news.ycombinator.com")):
                if site in lowered:
                    url = dom
                    break
        # For news/headline intent, prefer the site's RSS feed — its homepage is
        # JS-rendered and contains no readable headlines, but the RSS feed does.
        news_intent = any(w in lowered for w in ("news", "headline", "latest", "top stories"))
        if url and news_intent:
            host = url.split("//")[-1].split("/")[0].lower()
            rss = {
                # CNN's free RSS is frozen; its text-only site is static & current.
                "cnn.com": "https://lite.cnn.com",
                "www.cnn.com": "https://lite.cnn.com",
                "bbc.com": "http://feeds.bbci.co.uk/news/rss.xml",
                "www.bbc.com": "http://feeds.bbci.co.uk/news/rss.xml",
            }.get(host)
            if rss:
                url = rss
        if url:
            calls.append({"preset": "web_fetch", "args": {"url": url}, "raw": "[[forced]]"})

        # 2. Network / IP address.
        if "ip address" in lowered or "ipconfig" in lowered or near(("my", "ip")) or near(("public", "ip")) or near(("what", "ip")):
            calls.append({"preset": "network_info", "args": {}, "raw": "[[forced]]"})

        # 3. Read a specific file (works even when a listing was injected).
        rm = re.search(r'(?:read|open|show|cat|contents? of|content of)\s+(?:the\s+)?(?:file\s+)?([\w\-./\\]+\.\w+)', lowered)
        if rm and rm.group(1).rsplit(".", 1)[-1] not in KNOWN_TLDS:
            calls.append({"preset": "file_explorer", "args": {"action": "read", "path": rm.group(1)}, "raw": "[[forced]]"})

        # 4. List files — skip when the workspace listing was already injected.
        if not context_injected:
            list_kw = ("list files", "list directory", "show files", "what files", "which files",
                       "list all files", "list the files", "show all files", "give me the files")
            if any(k in lowered for k in list_kw) or near(("list", "files")) or near(("list", "directory")) or near(("show", "files")) or near(("all", "files")):
                path = "."
                m = re.search(r'(?:in|under|from|at)\s+([\w\-/.\\:]+)', lowered)
                if m and m.group(1) not in ("the", "a", "this", "that", "my", "your"):
                    path = m.group(1)
                calls.append({"preset": "file_explorer", "args": {"action": "list", "path": path}, "raw": "[[forced]]"})

        # 5. Search.
        if near(("search", "for")) or near(("find", "code")) or near(("find", "function")) or "grep" in lowered:
            qm = re.search(r'["\']([^"\']+)["\']', prompt_text)
            query = qm.group(1) if qm else "def"
            calls.append({"preset": "search_ripgrep", "args": {"query": query, "path": "."}, "raw": "[[forced]]"})

        logger.info("[TOOL_TRACE] FORCE_MATCH presets=%s", [c["preset"] for c in calls])
        return calls

    def _build_continuation_prompt(self, original_prompt: str, last_response: str, tool_results: list):
        import json
        parts = ["=== ORIGINAL USER REQUEST ==="]
        parts.append(original_prompt)
        parts.append("\n=== YOUR PREVIOUS ATTEMPT ===")
        parts.append(last_response)
        parts.append("\n=== TOOL EXECUTION RESULTS (USE THESE TO ANSWER) ===")
        for tr in tool_results:
            parts.append(f"\nTool: {tr['call']['preset']}")
            parts.append(f"Args: {json.dumps(tr['call']['args'])}")
            # Cap each result so a big page/listing doesn't blow up the context
            # and slow generation to the point of timing out.
            result_json = json.dumps(tr['result'])
            if len(result_json) > 2500:
                result_json = result_json[:2500] + " …(truncated)"
            parts.append(f"Result: {result_json}")
        parts.append("\n=== INSTRUCTION ===")
        parts.append("Using the TOOL EXECUTION RESULTS above, provide a direct answer to the ORIGINAL USER REQUEST.")
        parts.append("Do NOT describe what you would do. Do NOT explain the tools.")
        parts.append("Answer with the actual data from the results.")
        return "\n".join(parts)

    async def _mcp_invoke(self, req: Request):
        body = await req.json()
        preset = body.get("preset", "")
        args = body.get("args", {})
        workspace = self._resolve_workspace(body.get("workspace_folder", "")) or None
        if not preset:
            return {"error": "missing_preset"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        try:
            result = await mcp_cell.invoke(preset, args, workspace=workspace)
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

    async def _ollama_ps(self):
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(f"{settings.ollama_host}/api/ps")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", m.get("model", "")) for m in data.get("models", [])]
                    return {"models": models, "zero_loaded": len(models) == 0}
                return {"models": [], "zero_loaded": True, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"models": [], "zero_loaded": True, "error": str(e)}

    async def _unload_model(self, req: Request):
        body = await req.json()
        model = body.get("model", "")
        if not model:
            return {"error": "missing_model"}
        runtime = getattr(self._gateway, "_runtime", None)
        if not runtime:
            return {"error": "runtime_not_available"}
        try:
            ok = await runtime._model_manager.unload(model)
            verify = await runtime._model_manager.verify_zero_loaded()
            return {"unloaded": ok, "verification": verify}
        except Exception as e:
            return {"error": str(e)}

    async def _execute_plan(self, req: Request):
        import json
        body = await req.json()
        plan_text = body.get("plan", "")
        workspace_folder = self._resolve_workspace(body.get("workspace_folder", ""))
        if not plan_text:
            return {"error": "empty_plan"}
        mcp_cell = getattr(self._gateway, "_mcp", None)
        if not mcp_cell:
            return {"error": "mcp_not_available"}
        tool_calls = self._extract_tool_calls(plan_text)
        if not tool_calls:
            return {"status": "no_tools_found", "plan": plan_text[:500]}
        results = []
        for tc in tool_calls:
            args = tc["args"]
            if workspace_folder:
                wf = Path(workspace_folder)
                for key in ("path", "dest"):
                    if key in args and isinstance(args[key], str):
                        if not Path(args[key]).is_absolute():
                            args[key] = str(wf / args[key])
            result = await mcp_cell.invoke(tc["preset"], args, workspace=workspace_folder or None)
            results.append({"tool": tc["preset"], "args": tc["args"], "result": result})
        return {"status": "executed", "results": results}

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
