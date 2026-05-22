"""tests/mcp/test_all_presets.py — Every MCP preset must run with valid args and zero errors.

This exercises all 14 production presets through the real process-isolated worker,
jailed to a temporary workspace, to guarantee the whole tool ecosystem works.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from cells.mcp.cell import MCPCell


# (preset, args) — happy-path arguments for each tool.
CASES = [
    ("file_explorer", {"action": "list", "path": "."}),
    ("file_explorer", {"action": "read", "path": "sample.py"}),
    ("file_explorer", {"action": "write", "path": "written.txt", "content": "hi"}),
    ("file_explorer", {"action": "stat", "path": "sample.py"}),
    ("file_explorer", {"action": "mkdir", "path": "subdir"}),
    ("code_analyzer", {"path": "sample.py"}),
    ("git_mcp", {"action": "status"}),
    ("search_ripgrep", {"query": "hello", "path": "."}),
    ("python_exec", {"code": "print(6 * 7)"}),
    ("diff_engine", {"action": "text", "a": "foo\n", "b": "bar\n"}),
    ("refactor_safe", {"action": "rename_symbol", "path": "sample.py", "old": "hello", "new": "hi"}),
    ("doc_generator", {"path": "sample.py"}),
    ("dependency_inspector", {"path": "."}),
    ("workspace_indexer", {"path": "."}),
    ("health_monitor", {}),
    ("project_scaffold", {"template": "python", "name": "scaffold_test", "path": "."}),
    ("rollback_manager", {"action": "snapshot", "path": "sample.py"}),
    ("structured_terminal", {"command": "pwd"}),
    ("structured_terminal", {"command": "ls", "path": "."}),
    ("network_info", {}),  # local IP works without internet
]


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "sample.py").write_text("def hello():\n    return 'hello world'\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("some notes\n", encoding="utf-8")
    return str(tmp_path)


@pytest.mark.asyncio
async def test_every_preset_runs_without_error(workspace):
    ws = workspace
    cell = MCPCell()
    await cell.init()
    failures = []
    for preset, args in CASES:
        result = await cell.invoke(preset, dict(args), workspace=ws)
        if not isinstance(result, dict) or "error" in result:
            failures.append((preset, args, result))
    assert not failures, "Presets returned errors:\n" + "\n".join(
        f"  {p} {a} -> {r}" for p, a, r in failures
    )


@pytest.mark.asyncio
async def test_all_presets_are_registered():
    cell = MCPCell()
    await cell.init()
    names = {t["name"] for t in cell.list_tools()}
    expected = {
        "file_explorer", "code_analyzer", "git_mcp", "search_ripgrep", "python_exec",
        "diff_engine", "refactor_safe", "doc_generator", "dependency_inspector",
        "workspace_indexer", "health_monitor", "project_scaffold", "rollback_manager",
        "structured_terminal", "web_fetch", "network_info",
    }
    missing = expected - names
    assert not missing, f"missing presets: {missing}"
