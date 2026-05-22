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


def make_server(mcp_cell):
    gateway = FakeGateway(mcp_cell=mcp_cell)
    server = RESTServer(gateway=gateway)
    return server


def make_fake_httpx(response_text: str):
    """Return a monkeypatch target that replaces httpx.AsyncClient."""
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"response": response_text, "done": True}
        def text(self):
            return ""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
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
    """FakeClient that records every /api/generate payload it receives."""
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"response": response_text, "done": True}
        def text(self):
            return ""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, *args, **kwargs):
            if "generate" in str(url):
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
    assert main_call["options"]["num_predict"] == 2048, "output must be capped"
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
async def test_workspace_folder_is_passed_to_mcp(monkeypatch):
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
                "workspace_folder": "/tmp/my_project",
            }

    await server._handle_prompt(FakeReq())
    assert mcp.invocations, "expected at least the workspace listing invocation"
    assert mcp.last_workspace == "/tmp/my_project"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
