"""tests/observability/test_trace_propagation.py — Verify trace_id propagation."""
from __future__ import annotations
import pytest
from kernel.observability.trace_context import (
    generate_trace_id,
    get_trace_id,
    set_trace_id,
    clear_trace_id,
)


def test_generate_trace_id_format():
    tid = generate_trace_id()
    assert tid.startswith("TRACE-")
    parts = tid.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 6  # ######


def test_trace_id_uniqueness():
    ids = {generate_trace_id() for _ in range(100)}
    assert len(ids) == 100


def test_get_set_clear_trace_id():
    assert get_trace_id() is None
    set_trace_id("TRACE-20250101-000001")
    assert get_trace_id() == "TRACE-20250101-000001"
    clear_trace_id()
    assert get_trace_id() is None


@pytest.mark.asyncio
async def test_trace_id_async_propagation():
    """Trace ID must propagate through async context."""
    import asyncio

    set_trace_id("TRACE-ASYNC-001")

    async def inner():
        return get_trace_id()

    result = await inner()
    assert result == "TRACE-ASYNC-001"
    clear_trace_id()
