"""plasma/run_store.py — Persisted Runs + Run Events (Phase A).

A "Run" is one agent turn executed as a background job, modeled on the OpenAI
Assistants Run lifecycle. Every run has a status and an append-only event log
with a monotonic per-run sequence number — this single log powers both SSE
streaming (Phase B) and resume-by-seq (Phase C, Discord-style replay).

Schema lives in the existing plasma SQLite DB (WAL mode).
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from kernel.config import settings

# Run lifecycle statuses (subset of OpenAI's, adapted to local single-runtime).
QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"  # process died mid-run; recoverable
TERMINAL = {COMPLETED, FAILED, CANCELLED, INTERRUPTED}

# Event types in the run log.
EV_TOKEN = "token"
EV_TOOL_STARTED = "tool_started"
EV_TOOL_RESULT = "tool_result"
EV_STATUS = "status"
EV_HEARTBEAT = "heartbeat"
EV_DONE = "done"
EV_ERROR = "error"


class RunStore:
    """CRUD for runs and their event logs. Thread-safe via a single WAL conn."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (settings.data_dir / "plasma.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                session_id TEXT,
                agent TEXT,
                model TEXT,
                status TEXT,
                prompt TEXT,
                partial_output TEXT DEFAULT '',
                error TEXT,
                created_at REAL,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS run_events (
                run_id TEXT,
                seq INTEGER,
                type TEXT,
                data TEXT,
                ts REAL,
                PRIMARY KEY (run_id, seq)
            );
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
            CREATE INDEX IF NOT EXISTS idx_events_run ON run_events(run_id, seq);
            """
        )
        self._conn.commit()

    # ── runs ──
    def create_run(self, session_id: str, agent: str, model: str, prompt: str) -> str:
        run_id = f"run-{uuid.uuid4().hex[:16]}"
        now = time.time()
        self._conn.execute(
            "INSERT INTO runs (run_id, session_id, agent, model, status, prompt, "
            "partial_output, error, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, session_id, agent, model, QUEUED, prompt, "", None, now, now),
        )
        self._conn.commit()
        return run_id

    def set_status(self, run_id: str, status: str, error: Optional[str] = None):
        self._conn.execute(
            "UPDATE runs SET status=?, error=COALESCE(?, error), updated_at=? WHERE run_id=?",
            (status, error, time.time(), run_id),
        )
        self._conn.commit()
        # Mirror status changes into the event log so streams observe them.
        self.append_event(run_id, EV_STATUS, {"status": status, "error": error})

    def append_output(self, run_id: str, text: str):
        """Append generated text to the run's persisted partial output."""
        self._conn.execute(
            "UPDATE runs SET partial_output = partial_output || ?, updated_at=? WHERE run_id=?",
            (text, time.time(), run_id),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> Optional[dict]:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_active(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM runs WHERE status IN (?,?)", (QUEUED, RUNNING)
        ).fetchall()
        return [dict(r) for r in rows]

    def recover_interrupted(self) -> int:
        """On startup: any run still 'running'/'queued' is orphaned → mark
        interrupted. Returns how many were recovered. Partial output is kept."""
        rows = self.list_active()
        for r in rows:
            self.set_status(r["run_id"], INTERRUPTED, error="backend_restarted")
        return len(rows)

    # ── events ──
    def append_event(self, run_id: str, type_: str, data) -> int:
        """Append an event with the next monotonic seq for this run. Returns seq."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS m FROM run_events WHERE run_id=?", (run_id,)
        ).fetchone()
        seq = int(row["m"]) + 1
        self._conn.execute(
            "INSERT INTO run_events (run_id, seq, type, data, ts) VALUES (?,?,?,?,?)",
            (run_id, seq, type_, json.dumps(data), time.time()),
        )
        self._conn.commit()
        return seq

    def events_since(self, run_id: str, after_seq: int = 0) -> list[dict]:
        """Replay events with seq > after_seq (Discord-style resume)."""
        rows = self._conn.execute(
            "SELECT seq, type, data, ts FROM run_events WHERE run_id=? AND seq>? ORDER BY seq",
            (run_id, after_seq),
        ).fetchall()
        out = []
        for r in rows:
            out.append({"seq": r["seq"], "type": r["type"], "data": json.loads(r["data"]), "ts": r["ts"]})
        return out

    def max_seq(self, run_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS m FROM run_events WHERE run_id=?", (run_id,)
        ).fetchone()
        return int(row["m"])


# Singleton
run_store = RunStore()
