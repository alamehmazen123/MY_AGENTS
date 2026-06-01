"""kernel/observability/logger.py — Rotating loggers with trace_id injection."""
from __future__ import annotations
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

from kernel.config import settings
from kernel.observability.trace_context import get_trace_id


class _TraceFilter(logging.Filter):
    """Inject trace_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = get_trace_id()
        record.trace_id = trace_id or "NO_TRACE"
        return True


class _SizedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that ensures the directory exists before rotating."""

    def __init__(self, filename: str | Path, max_bytes: int, backup_count: int):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count)


def _make_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(f"my_agents.observability.{name}")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on re-import / reload
    if any(isinstance(h, (_SizedRotatingFileHandler, logging.StreamHandler)) for h in logger.handlers):
        return logger

    log_dir = settings.observability_log_dir
    log_path = log_dir / filename

    handler = _SizedRotatingFileHandler(
        log_path,
        max_bytes=settings.observability_max_log_mb * 1024 * 1024,
        backup_count=settings.observability_max_log_backups,
    )

    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(trace_id)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(_TraceFilter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger


# Phase-specific loggers --------------------------------------------------
execution_timeline_logger = _make_logger("execution_timeline", "execution_timeline.log")
mcp_trace_logger = _make_logger("mcp_trace", "mcp_trace.log")
agent_reasoning_logger = _make_logger("agent_reasoning", "agent_reasoning.log")
performance_logger = _make_logger("performance", "performance.log")
failure_logger = _make_logger("failure", "failures.log")


_LOG_NAME_MAP = {
    "execution_timeline": "execution_timeline.log",
    "mcp_trace": "mcp_trace.log",
    "agent_reasoning": "agent_reasoning.log",
    "performance": "performance.log",
    "failure": "failures.log",
}


def tail_log_file(name: str, lines: int = 100) -> list[str]:
    """Tail the last N lines from a named observability log file.
    Returns empty list if file does not exist or name is unknown."""
    filename = _LOG_NAME_MAP.get(name)
    if not filename:
        return []
    log_path = settings.observability_log_dir / filename
    if not log_path.exists():
        return []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        return [line.rstrip("\n") for line in all_lines[-lines:]]
    except Exception:
        return []


def list_log_files() -> list[dict]:
    """Return metadata for all observability log files."""
    result = []
    for name, filename in _LOG_NAME_MAP.items():
        log_path = settings.observability_log_dir / filename
        size = log_path.stat().st_size if log_path.exists() else 0
        result.append({"name": name, "filename": filename, "size_bytes": size})
    return result
