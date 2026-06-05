"""tests/test_chat_tool_execution.py — Automated regression tests for chat tool execution.

PHASE 10 — BUILD AUTOMATED REGRESSION TESTS

These tests verify that Agent-A executes real tools rather than hallucinating
explanations when the user requests file operations.
"""
from __future__ import annotations
import asyncio
import json
import pytest
from pathlib import Path

# Ensure project root on path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cells.gateway.rest import RESTServer


class FakeGateway:
    def __init__(self, mcp_cell=None):
        self._mcp = mcp_cell


class FakeMCPCell:
    def __init__(self, responses: dict | None = None):
        self._responses = responses or {}
        self.invocations: list[tuple[str, dict]] = []

    async def invoke(self, preset: str, args: dict, workspace: str | None = None) -> dict:
        self.invocations.append((preset, args))
        self.last_workspace = workspace
        if preset in self._responses:
            return self._responses[preset]
        # Default realistic responses
        if preset == "file_explorer" and args.get("action") == "list":
            return {"items": [{"name": "main.py", "type": "file", "size": 123}, {"name": "README.md", "type": "file", "size": 456}]}
        if preset == "file_explorer" and args.get("action") == "read":
            return {"content": "def main(): pass\n", "path": args.get("path", ""), "name": Path(args.get("path", "")).name}
        if preset == "search_ripgrep":
            return {"matches": [{"file": "main.py", "line": 1, "text": "def main():"}]}
        return {"error": "no_mock", "preset": preset, "args": args}

    def list_tools(self):
        return [
            {"name": "file_explorer", "description": "Browse files"},
            {"name": "search_ripgrep", "description": "Search text"},
            {"name": "python_exec", "description": "Run Python"},
        ]

    def ollama_tools(self, names=None):
        return []


def make_server(mcp_cell):
    gateway = FakeGateway(mcp_cell=mcp_cell)
    server = RESTServer(gateway=gateway)
    return server


import json as _json


class _FakeStream:
    """Async context manager mimicking httpx client.stream() for /api/chat NDJSON."""
    def __init__(self, lines, status=200):
        self.status_code = status
        self._lines = lines
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        pass
    async def aiter_lines(self):
        for ln in self._lines:
            yield ln


def _chat_ndjson(content: str, tool_calls=None):
    return [_json.dumps({"message": {"content": content, "tool_calls": tool_calls}, "done": True})]


def make_fake_httpx(response_text: str, tool_calls=None):
    """Return a monkeypatch target that replaces httpx.AsyncClient.
    Mimics Ollama streaming /api/chat plus plain GET/POST (unload)."""
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"models": [], "done": True}
        def text(self):
            return ""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def stream(self, method, url, **kwargs):
            return _FakeStream(_chat_ndjson(response_text, tool_calls))
        async def post(self, *args, **kwargs):
            return FakeResponse()
        async def get(self, *args, **kwargs):
            return FakeResponse()

    return FakeClient


@pytest.mark.asyncio
async def test_prompt_list_files_forces_tool(monkeypatch):
    """Test 1: Prompt 'List current directory' MUST invoke file_explorer."""
    mcp = FakeMCPCell()
    server = make_server(mcp)

    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("You can use file_explorer by..."))

    class FakeReq:
        async def json(self):
            return {
                "prompt": "List current directory",
                "model": "dummy",
                "system": "You are a helper.",
                "no_tools": False,
            }

    result = await server._handle_prompt(FakeReq())
    assert len(mcp.invocations) >= 1, f"Expected at least 1 tool invocation, got {mcp.invocations}"
    assert mcp.invocations[0][0] == "file_explorer"
    assert mcp.invocations[0][1].get("action") == "list"


@pytest.mark.asyncio
async def test_prompt_read_file_forces_tool(monkeypatch):
    """Test 2: Prompt 'Read debug_trace.py' MUST invoke file_explorer.read."""
    mcp = FakeMCPCell()
    server = make_server(mcp)

    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("The file contains Python code."))

    class FakeReq:
        async def json(self):
            return {
                "prompt": "Read debug_trace.py",
                "model": "dummy",
                "system": "You are a helper.",
                "no_tools": False,
            }

    result = await server._handle_prompt(FakeReq())
    assert any(inv[0] == "file_explorer" and inv[1].get("action") == "read" for inv in mcp.invocations), \
        f"Expected file_explorer read invocation, got {mcp.invocations}"


@pytest.mark.asyncio
async def test_prompt_search_code_forces_tool(monkeypatch):
    """Test 3: Prompt 'Search for worker_process' MUST invoke search_ripgrep."""
    mcp = FakeMCPCell()
    server = make_server(mcp)

    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("You can search using ripgrep..."))

    class FakeReq:
        async def json(self):
            return {
                "prompt": "Search for worker_process",
                "model": "dummy",
                "system": "You are a helper.",
                "no_tools": False,
            }

    result = await server._handle_prompt(FakeReq())
    assert any(inv[0] == "search_ripgrep" for inv in mcp.invocations), \
        f"Expected search_ripgrep invocation, got {mcp.invocations}"


def test_extract_tool_calls_tolerates_python_triple_quotes():
    """Regression: the model often writes content with Python triple-quotes,
    which is invalid JSON. The extractor must still recover it."""
    server = make_server(FakeMCPCell())
    text = (
        '[[MCP:file_explorer:{"action":"write","path":"x.py",'
        '"content":"""def f():\n    return 1\n"""}]]'
    )
    calls = server._extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["preset"] == "file_explorer"
    assert calls[0]["args"]["action"] == "write"
    assert "def f()" in calls[0]["args"]["content"]


def test_extract_tool_calls_tolerates_single_quotes():
    server = make_server(FakeMCPCell())
    text = "[[MCP:file_explorer:{'action':'list','path':'.'}]]"
    calls = server._extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["args"]["action"] == "list"


@pytest.mark.asyncio
async def test_extract_tool_calls_multiline_json():
    """Test that _extract_tool_calls handles multi-line JSON."""
    server = make_server(FakeMCPCell())
    text = '''Some text before
[[MCP:file_explorer:{
  "action": "list",
  "path": "."
}]]
Some text after'''
    calls = server._extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["preset"] == "file_explorer"
    assert calls[0]["args"] == {"action": "list", "path": "."}


@pytest.mark.asyncio
async def test_extract_tool_calls_markdown_block():
    """Test that _extract_tool_calls finds calls inside markdown code blocks."""
    server = make_server(FakeMCPCell())
    text = '''Here is the tool call:
```
[[MCP:search_ripgrep:{"query":"hello","path":"."}]]
```
'''
    calls = server._extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["preset"] == "search_ripgrep"
    assert calls[0]["args"] == {"query": "hello", "path": "."}


@pytest.mark.asyncio
async def test_no_tools_flag_disables_forced_detection(monkeypatch):
    """Test that no_tools=True prevents forced tool execution."""
    mcp = FakeMCPCell()
    server = make_server(mcp)

    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("You can use file_explorer by..."))

    class FakeReq:
        async def json(self):
            return {
                "prompt": "List current directory",
                "model": "dummy",
                "system": "You are a helper.",
                "no_tools": True,
            }

    result = await server._handle_prompt(FakeReq())
    assert len(mcp.invocations) == 0, f"Expected 0 invocations with no_tools=True, got {mcp.invocations}"


def make_recording_httpx(response_text: str, posts: list):
    """FakeClient that records the streamed /api/chat payload and the /api/generate
    unload payload, so tests can assert num_predict, keep_alive, and the unload."""
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"models": [], "done": True}
        def text(self):
            return ""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def stream(self, method, url, **kwargs):
            posts.append(kwargs.get("json", {}))
            return _FakeStream(_chat_ndjson(response_text))
        async def post(self, url, *args, **kwargs):
            if "generate" in str(url):  # the unload call
                posts.append(kwargs.get("json", {}))
            return FakeResponse()
        async def get(self, *args, **kwargs):
            return FakeResponse()

    return FakeClient


@pytest.mark.asyncio
async def test_generation_caps_output_and_keeps_model_resident(monkeypatch):
    """Regression: every generate call must cap num_predict and keep the model
    resident (keep_alive != 0) during the loop, with a single unload at the end."""
    posts: list = []
    server = make_server(FakeMCPCell())
    monkeypatch.setattr("httpx.AsyncClient", make_recording_httpx("Just a plain answer.", posts))

    class FakeReq:
        async def json(self):
            return {"prompt": "explain recursion", "model": "dummy", "no_tools": True}

    await server._handle_prompt(FakeReq())

    # At least the main generate + the final unload generate were sent.
    assert len(posts) >= 2
    main_call = posts[0]
    assert main_call["options"]["num_predict"] == 1024, "output must be capped"
    assert main_call["keep_alive"] == "5m", "model must stay resident during the turn"
    # The last call is the explicit unload.
    assert posts[-1]["keep_alive"] == 0, "turn must end with a single unload"


@pytest.mark.asyncio
async def test_forced_tool_fires_only_once(monkeypatch):
    """Regression: a 'list files' request must invoke file_explorer exactly once,
    not loop the maximum number of iterations (the old hang)."""
    mcp = FakeMCPCell()
    server = make_server(mcp)
    # Model never emits a real tool call, so only forced detection can fire.
    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("Here is some prose without any tool call."))

    class FakeReq:
        async def json(self):
            return {"prompt": "list the files in the current directory", "model": "dummy", "no_tools": False}

    await server._handle_prompt(FakeReq())
    file_calls = [i for i in mcp.invocations if i[0] == "file_explorer"]
    assert len(file_calls) == 1, f"forced tool must fire once, got {len(file_calls)}: {mcp.invocations}"


@pytest.mark.asyncio
async def test_missing_model_fails_fast(monkeypatch):
    """Regression: an uninstalled model returns a clear error instead of hanging."""
    server = make_server(FakeMCPCell())

    class ModelListResponse:
        status_code = 200
        def json(self):
            return {"models": [{"name": "qwen3:4b"}, {"name": "deepseek-coder:1.3b"}]}
        def text(self):
            return ""

    class FakeClient:
        def __init__(self, *a, **k):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        async def get(self, *a, **k):
            return ModelListResponse()
        async def post(self, *a, **k):
            raise AssertionError("should not call generate for a missing model")

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)

    class FakeReq:
        async def json(self):
            return {"prompt": "hi", "model": "not-installed:99b", "no_tools": True}

    result = await server._handle_prompt(FakeReq())
    assert result.get("error") == "model_not_installed"


@pytest.mark.asyncio
async def test_workspace_folder_is_passed_to_mcp(monkeypatch, tmp_path):
    """Regression: the user-selected folder must reach MCP so the jail follows it."""
    mcp = FakeMCPCell()
    server = make_server(mcp)
    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("prose, no tool call"))

    class FakeReq:
        async def json(self):
            return {
                "prompt": "list current directory",
                "model": "dummy",
                "no_tools": False,
                "workspace_folder": str(tmp_path),
            }

    await server._handle_prompt(FakeReq())
    assert mcp.invocations, "expected at least the workspace listing invocation"
    assert mcp.last_workspace == str(tmp_path.resolve())


@pytest.mark.asyncio
async def test_core_instructions_reach_the_model(monkeypatch):
    """PROOF: the project-wide core instructions are included in the system prompt
    of the ACTUAL payload sent to the model on every prompt."""
    posts: list = []
    server = make_server(FakeMCPCell())
    monkeypatch.setattr("httpx.AsyncClient", make_recording_httpx("ok", posts))

    class FakeReq:
        async def json(self):
            return {"prompt": "anything", "model": "dummy", "no_tools": True}

    await server._handle_prompt(FakeReq())

    assert posts, "no chat call captured"
    # System prompt now lives in the first chat message (role=system).
    msgs = posts[0].get("messages", [])
    system = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
    # Distinctive phrases that exist ONLY in core_instructions.md (runtime rules).
    assert "Core agent instructions" in system, f"core instructions missing: {system[:200]}"
    assert "NEVER invent data" in system
    assert "ask the user for clarification" in system


@pytest.mark.asyncio
async def test_native_tool_calls_are_executed(monkeypatch):
    """P1: a native Ollama `message.tool_calls` must be executed (no regex)."""
    mcp = FakeMCPCell()
    server = make_server(mcp)
    native = [{"function": {"name": "file_explorer", "arguments": {"action": "list", "path": "."}}}]
    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("", tool_calls=native))

    class FakeReq:
        async def json(self):
            return {"prompt": "list files", "model": "dummy", "no_tools": False}

    await server._handle_prompt(FakeReq())
    assert any(i[0] == "file_explorer" and i[1].get("action") == "list" for i in mcp.invocations), \
        f"native tool call must run, got {mcp.invocations}"


def test_native_tool_calls_parser():
    """Native tool_calls (incl. stringified args) convert to the internal shape."""
    server = make_server(FakeMCPCell())
    out = server._native_tool_calls([
        {"function": {"name": "calculator", "arguments": {"expression": "2+2"}}},
        {"function": {"name": "clock", "arguments": "{\"timezone\": \"Asia/Tokyo\"}"}},
    ])
    assert out[0]["preset"] == "calculator" and out[0]["args"]["expression"] == "2+2"
    assert out[1]["preset"] == "clock" and out[1]["args"]["timezone"] == "Asia/Tokyo"
    assert server._native_tool_calls(None) == []


@pytest.mark.asyncio
async def test_verify_python_writes_pass_and_fail():
    """P4: a clean .py write verifies ✅; a broken one reports ❌ with the line."""
    server = make_server(FakeMCPCell())
    good = {"call": {"preset": "file_explorer", "args": {"action": "write", "path": "a.py", "content": "def f():\n    return 1\n"}},
            "result": {"path": "a.py"}}
    bad = {"call": {"preset": "file_explorer", "args": {"action": "write", "path": "b.py", "content": "def f(:\n    return 1\n"}},
           "result": {"path": "b.py"}}
    out_good = await server._verify_python_writes(FakeMCPCell(), [good], None)
    out_bad = await server._verify_python_writes(FakeMCPCell(), [bad], None)
    assert "✅" in out_good and "a.py" in out_good
    assert "❌" in out_bad and "b.py" in out_bad and "syntax error" in out_bad
    # Non-.py writes are ignored.
    txt = {"call": {"preset": "file_explorer", "args": {"action": "write", "path": "n.txt", "content": "hi"}}, "result": {"path": "n.txt"}}
    assert await server._verify_python_writes(FakeMCPCell(), [txt], None) == ""


@pytest.mark.asyncio
async def test_never_empty_output_when_model_only_tool_calls(monkeypatch):
    """Regression: a model that only emits tool calls and never text (e.g.
    llama3.2:3b spamming web_fetch) must NOT yield an empty '[No response]'."""
    mcp = FakeMCPCell()
    server = make_server(mcp)
    native = [{"function": {"name": "file_explorer", "arguments": {"action": "list", "path": "."}}}]
    # content '' on every call → model never produces text.
    monkeypatch.setattr("httpx.AsyncClient", make_fake_httpx("", tool_calls=native))

    class FakeReq:
        async def json(self):
            return {"prompt": "do something with tools", "model": "dummy", "no_tools": False}

    result = await server._handle_prompt(FakeReq())
    assert result["output"].strip(), "output must never be blank"
    assert "no written answer" in result["output"], result["output"][:120]


def test_is_destructive():
    server = make_server(FakeMCPCell())
    assert server._is_destructive("file_explorer", {"action": "delete", "path": "x"})
    assert server._is_destructive("file_explorer", {"action": "write", "path": "x"})
    assert server._is_destructive("structured_terminal", {"command": "rm", "target": "x"})
    assert server._is_destructive("python_exec", {"code": "print(1)"})
    assert not server._is_destructive("file_explorer", {"action": "read", "path": "x"})
    assert not server._is_destructive("search_ripgrep", {"query": "x"})
    assert not server._is_destructive("web_fetch", {"url": "x"})


@pytest.mark.asyncio
async def test_guarded_invoke_refuses_broken_python():
    """Gather→implement safety: syntactically-broken .py writes are refused."""
    mcp = FakeMCPCell()
    server = make_server(mcp)
    out = await server._guarded_invoke(
        mcp, "file_explorer", {"action": "write", "path": "x.py", "content": "def f(:\n  pass\n"}, None, "auto")
    assert out.get("error") == "syntax_error"
    assert not mcp.invocations, "broken python must NOT be written"
    # Valid python passes through.
    await server._guarded_invoke(
        mcp, "file_explorer", {"action": "write", "path": "y.py", "content": "def f():\n    return 1\n"}, None, "auto")
    assert any(i[1].get("path") == "y.py" for i in mcp.invocations)


@pytest.mark.asyncio
async def test_guarded_invoke_refuses_truncated_rewrite(tmp_path):
    """A much-smaller rewrite of an existing .py (likely truncation) is refused."""
    big = tmp_path / "big.py"
    big.write_text("# header\n" + "\n".join(f"def f{i}():\n    return {i}" for i in range(80)), encoding="utf-8")
    mcp = FakeMCPCell()
    server = make_server(mcp)
    out = await server._guarded_invoke(
        mcp, "file_explorer", {"action": "write", "path": "big.py", "content": "def f0():\n    return 0\n"},
        str(tmp_path), "auto")
    assert out.get("error") == "truncation_guard"
    assert not mcp.invocations, "truncated rewrite must NOT overwrite the file"


@pytest.mark.asyncio
async def test_guarded_invoke_blocks_in_ask_mode():
    mcp = FakeMCPCell()
    server = make_server(mcp)
    # Ask mode: a delete is blocked (not executed).
    out = await server._guarded_invoke(mcp, "file_explorer", {"action": "delete", "path": "x"}, None, "ask")
    assert out.get("error") == "requires_permission"
    assert not any(i[0] == "file_explorer" for i in mcp.invocations), "destructive call must NOT run in ask mode"
    # Ask mode: a read still runs.
    await server._guarded_invoke(mcp, "file_explorer", {"action": "list", "path": "."}, None, "ask")
    assert any(i[0] == "file_explorer" for i in mcp.invocations)
    # Auto mode: delete runs.
    mcp.invocations.clear()
    await server._guarded_invoke(mcp, "file_explorer", {"action": "delete", "path": "x"}, None, "auto")
    assert any(i[1].get("action") == "delete" for i in mcp.invocations)


def test_is_plan_request():
    server = make_server(FakeMCPCell())
    assert server._is_plan_request("make a list for improvement of coding for this project")
    assert server._is_plan_request("how to improve the project")
    assert server._is_plan_request("review this project and suggest changes")
    assert not server._is_plan_request("what is the weather today")
    assert not server._is_plan_request("read todo.txt")


def test_build_code_map_grounds_on_real_files(tmp_path):
    """Planning code map lists real source files + a correct project profile."""
    (tmp_path / "cells").mkdir()
    (tmp_path / "cells" / "engine.py").write_text("def run():\n    return 1\n\nclass Engine:\n    pass\n", encoding="utf-8")
    (tmp_path / "kernel").mkdir()
    (tmp_path / "kernel" / "main.py").write_text("def boot():\n    pass\n", encoding="utf-8")
    fe = tmp_path / "frontend"
    fe.mkdir()
    (fe / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("x", encoding="utf-8")

    server = make_server(FakeMCPCell())
    cmap = server._build_code_map(str(tmp_path))
    assert "cells/engine.py" in cmap
    assert "kernel/main.py" in cmap
    assert "run" in cmap and "Engine" in cmap          # symbols extracted
    assert "NOT a CLI" in cmap                          # correct web-app profile
    assert "node_modules" not in cmap                   # scratch excluded


def test_curate_tools_is_bounded_and_relevant():
    """E: tool schemas are curated to a small relevant set, not all 39."""
    server = make_server(FakeMCPCell())
    # Plain prompt → just the core set.
    core = server._curate_tools("say hello")
    assert "file_explorer" in core and "calculator" in core
    assert "weather" not in core and "pdf_extract" not in core
    assert len(core) <= 16
    # Intent keyword pulls in the matching tool.
    weather = server._curate_tools("what's the weather forecast in Paris?")
    assert "weather" in weather
    pdf = server._curate_tools("extract text from report.pdf")
    assert "pdf_extract" in pdf
    # Always bounded.
    assert len(server._curate_tools("git weather pdf sql csv qr arxiv convert refactor dns html cpu scaffold rollback")) <= 16


def test_resolve_workspace(tmp_path):
    """Absolute dirs resolve; bogus names return '' (no silent wrong-folder)."""
    server = make_server(FakeMCPCell())
    assert server._resolve_workspace(str(tmp_path)) == str(tmp_path.resolve())
    assert server._resolve_workspace("") == ""
    assert server._resolve_workspace("definitely-not-a-real-folder-xyz-123") == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
