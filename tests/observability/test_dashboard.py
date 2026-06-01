"""tests/observability/test_dashboard.py — Verify dashboard endpoints."""
from __future__ import annotations
import pytest
from kernel.observability.dashboard import (
    get_dashboard_metrics,
    get_recent_traces,
    get_recent_failures,
)
from kernel.observability.recorder import recorder


def test_get_dashboard_metrics_structure():
    metrics = get_dashboard_metrics()
    assert isinstance(metrics, dict)
    assert "active_requests" in metrics
    assert "avg_latency_ms" in metrics
    assert "total_tool_calls" in metrics
    assert "failed_requests" in metrics
    assert "running_cells" in metrics
    assert "request_count" in metrics


def test_get_recent_traces_returns_list():
    traces = get_recent_traces(10)
    assert isinstance(traces, list)


def test_get_recent_failures_returns_list():
    failures = get_recent_failures(10)
    assert isinstance(failures, list)


def test_dashboard_integration():
    """Record some data and verify it appears in dashboard."""
    from kernel.observability.trace_context import set_trace_id, clear_trace_id

    set_trace_id("TRACE-DASH-001")
    recorder.record_mcp_call("test_tool", {"x": 1}, 10.0, "SUCCESS")
    recorder.record_failure("test_fail", None, {"detail": "none"})
    recorder.record_performance("test_component", 50.0)
    clear_trace_id()

    metrics = get_dashboard_metrics()
    assert metrics["total_tool_calls"] >= 1
    assert metrics["failed_requests"] >= 1
    assert metrics["request_count"] >= 1

    traces = get_recent_traces(5)
    assert any(t["tool"] == "test_tool" for t in traces)

    failures = get_recent_failures(5)
    assert any(f["category"] == "test_fail" for f in failures)
