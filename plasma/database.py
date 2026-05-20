"""
plasma/database.py — SQLite WAL, Connection Pool
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from kernel.config import settings


class Database:
    """SQLite with WAL mode and connection pooling."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.data_dir / "plasma.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._pool: list[sqlite3.Connection] = []
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                updated_at TEXT,
                state TEXT
            )
        """)
        conn.commit()
        self._pool.append(conn)
    
    @contextmanager
    def connection(self):
        conn = self._pool[0]
        try:
            yield conn
        finally:
            pass  # Pool reuse
    
    def execute(self, sql: str, params: tuple = ()):
        with self.connection() as conn:
            return conn.execute(sql, params)


# Singleton
db = Database()
