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

    async def invoke(self, preset: str, args: dict) -> dict:
        self.invocations.append((preset, args))
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
