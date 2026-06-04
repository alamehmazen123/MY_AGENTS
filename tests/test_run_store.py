"""tests/test_run_store.py — Phase A: persisted runs + resumable event log."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plasma.run_store import (
    RunStore, QUEUED, RUNNING, COMPLETED, INTERRUPTED,
    EV_TOKEN, EV_STATUS,
)


@pytest.fixture
def store(tmp_path):
    return RunStore(db_path=tmp_path / "t.db")


def test_create_and_get_run(store):
    rid = store.create_run("sess-1", "A", "qwen3:4b", "do a thing")
    run = store.get_run(rid)
    assert run["status"] == QUEUED
    assert run["agent"] == "A"
    assert run["model"] == "qwen3:4b"
    assert run["session_id"] == "sess-1"


def test_events_have_monotonic_seq(store):
    rid = store.create_run("s", "A", "m", "p")
    s1 = store.append_event(rid, EV_TOKEN, {"t": "hello"})
    s2 = store.append_event(rid, EV_TOKEN, {"t": " world"})
    assert s1 == 1 and s2 == 2
    assert store.max_seq(rid) == 2


def test_events_since_replays_only_newer(store):
    rid = store.create_run("s", "A", "m", "p")
    for i in range(5):
        store.append_event(rid, EV_TOKEN, {"i": i})
    # Resume from seq 2 → should return events 3,4,5 only (Discord-style replay).
    newer = store.events_since(rid, after_seq=2)
    assert [e["seq"] for e in newer] == [3, 4, 5]
    assert newer[0]["data"]["i"] == 2


def test_status_change_is_logged_as_event(store):
    rid = store.create_run("s", "A", "m", "p")
    store.set_status(rid, RUNNING)
    store.set_status(rid, COMPLETED)
    statuses = [e for e in store.events_since(rid) if e["type"] == EV_STATUS]
    assert [e["data"]["status"] for e in statuses] == [RUNNING, COMPLETED]


def test_append_output_accumulates(store):
    rid = store.create_run("s", "A", "m", "p")
    store.append_output(rid, "Hello")
    store.append_output(rid, ", world")
    assert store.get_run(rid)["partial_output"] == "Hello, world"


def test_recover_interrupted_marks_orphans(store):
    a = store.create_run("s", "A", "m", "p")
    b = store.create_run("s", "B", "m", "p")
    store.set_status(a, RUNNING)
    store.set_status(b, COMPLETED)
    recovered = store.recover_interrupted()
    assert recovered == 1  # only the still-running one
    assert store.get_run(a)["status"] == INTERRUPTED
    assert store.get_run(b)["status"] == COMPLETED
