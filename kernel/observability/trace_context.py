"""kernel/observability/trace_context.py — Trace ID generation and async propagation."""
from __future__ import annotations
import contextvars
import datetime
import itertools
import threading
from typing import Optional


_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)
_trace_counter = itertools.count(1)
_counter_lock = threading.Lock()


def generate_trace_id() -> str:
    """Generate a unique trace ID: TRACE-YYYYMMDD-######"""
    now = datetime.datetime.utcnow()
    with _counter_lock:
        count = next(_trace_counter)
    return f"TRACE-{now.strftime('%Y%m%d')}-{count:06d}"


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from async context."""
    return _trace_id_var.get(None)


def set_trace_id(trace_id: str) -> None:
    """Set the current trace ID in async context."""
    _trace_id_var.set(trace_id)


def clear_trace_id() -> None:
    """Clear the current trace ID from async context."""
    _trace_id_var.set(None)
