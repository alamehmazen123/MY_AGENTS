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
    # ── Tier 1/2 additions ──
    ("clock", {}),
    ("clock", {"timezone": "Asia/Tokyo"}),
    ("calculator", {"expression": "2*(3+4)**2/7"}),
    ("text_stats", {"text": "Hello world. This is a test."}),
    ("memory", {"action": "set", "key": "k", "value": "v"}),
    ("memory", {"action": "get", "key": "k"}),
    ("memory", {"action": "all"}),
    ("sequential_thinking", {"action": "add", "thought": "first step"}),
    ("sequential_thinking", {"action": "list"}),
    ("csv_json", {"path": "data.csv"}),
    ("sqlite_query", {"path": "test.db", "query": "SELECT 1 AS one"}),
    ("dns_lookup", {"host": "example.com"}),
    ("html_to_markdown", {"html": "<h1>Hi</h1><p>Body <a href='http://x.com'>link</a></p>"}),
    ("clipboard", {"action": "read"}),
    ("convert_units", {"value": 100, "from": "cm", "to": "m"}),
    ("convert_units", {"value": 32, "from": "f", "to": "c"}),
    ("process_monitor", {"top": 3}),
    ("qr_code", {"data": "https://example.com"}),
    ("sympy_math", {"action": "solve", "expression": "x**2 - 4", "variable": "x"}),
    ("sympy_math", {"action": "diff", "expression": "x**3", "variable": "x"}),
    ("pdf_extract", {"path": "sample.pdf"}),
    ("office_reader", {"path": "sample.docx"}),
]


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "sample.py").write_text("def hello():\n    return 'hello world'\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("some notes\n", encoding="utf-8")
    (tmp_path / "data.csv").write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

    import sqlite3
    con = sqlite3.connect(str(tmp_path / "test.db"))
    con.execute("CREATE TABLE t (id INTEGER)")
    con.execute("INSERT INTO t VALUES (1)")
    con.commit()
    con.close()

    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(tmp_path / "sample.pdf", "wb") as f:
        w.write(f)

    import docx
    d = docx.Document()
    d.add_paragraph("hello from docx")
    d.save(str(tmp_path / "sample.docx"))

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
        # Tier 1/2 additions
        "clock", "calculator", "text_stats", "memory", "sequential_thinking",
        "sqlite_query", "csv_json", "http_request", "wikipedia", "weather", "arxiv",
        "ip_geolocation", "dns_lookup", "html_to_markdown", "clipboard",
        "convert_units", "pdf_extract", "office_reader", "screenshot",
        "process_monitor", "qr_code", "sympy_math",
    }
    missing = expected - names
    assert not missing, f"missing presets: {missing}"
