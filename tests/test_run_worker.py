"""tests/test_run_worker.py — Phase A/B: background run worker persists a turn."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plasma.run_store as rs_mod
from plasma.run_store import RunStore, COMPLETED, FAILED, EV_DONE
from cells.gateway.rest import RESTServer


@pytest.fixture
def store(tmp_path, monkeypatch):
    s = RunStore(db_path=tmp_path / "runs.db")
    monkeypatch.setattr(rs_mod, "run_store", s)
    return s


@pytest.mark.asyncio
async def test_worker_persists_successful_turn(store, monkeypatch):
    server = RESTServer(gateway=None)

    async def fake_turn(body, emit=None):
        if emit:
            emit("tool_started", {"tool": "file_explorer"})
            emit("tool_result", {"tool": "file_explorer", "ok": True})
        return {"output": "All done.", "model": body["model"], "tool_results": [], "tool_context": ""}

    monkeypatch.setattr(server, "_run_turn", fake_turn)

    rid = store.create_run("s", "A", "qwen3:4b", "do it")
    await server._run_worker(rid, {"model": "qwen3:4b", "prompt": "do it"})

    run = store.get_run(rid)
    assert run["status"] == COMPLETED
    assert run["partial_output"] == "All done."
    types = [e["type"] for e in store.events_since(rid)]
    assert "tool_started" in types and "tool_result" in types and EV_DONE in types


@pytest.mark.asyncio
async def test_worker_records_failure(store, monkeypatch):
    server = RESTServer(gateway=None)

    async def boom(body, emit=None):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(server, "_run_turn", boom)
    rid = store.create_run("s", "A", "m", "p")
    await server._run_worker(rid, {"model": "m"})

    run = store.get_run(rid)
    assert run["status"] == FAILED
    assert "kaboom" in (run["error"] or "")
