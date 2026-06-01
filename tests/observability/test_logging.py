"""tests/observability/test_logging.py — Verify loggers and recorder."""
from __future__ import annotations
import time
import pytest
from kernel.observability.recorder import ObservabilityRecorder
from kernel.observability.trace_context import set_trace_id, clear_trace_id


@pytest.fixture
def fresh_recorder():
    """Return a fresh recorder instance for isolated tests."""
    rec = ObservabilityRecorder()
    clear_trace_id()
    return rec


def test_record_timeline_no_crash(fresh_recorder):
    fresh_recorder.record_timeline("Test", "event", 1.23)
    # Should not raise even when disabled or no file system


def test_record_mcp_call(fresh_recorder):
    set_trace_id("TRACE-TEST-001")
    fresh_recorder.record_mcp_call("file_explorer", {"path": "."}, 35.0, "SUCCESS")
    metrics = fresh_recorder.get_metrics()
    assert metrics["total_tool_calls"] == 1
    clear_trace_id()


def test_record_agent_reasoning(fresh_recorder):
    fresh_recorder.record_agent_reasoning(
        agent="Agent-A",
        prompt_length=1500,
        model="qwen3:4b",
        tools_detected=2,
        tools_executed=2,
        response_length=800,
    )


def test_record_performance_triggers_average(fresh_recorder, monkeypatch):
    """Verify that performance averaging triggers at the window boundary."""
    monkeypatch.setattr("kernel.config.settings.observability_performance_window", 5)
    for _ in range(5):
        fresh_recorder.record_performance("ollama", 100.0)
    # The 5th call should trigger average flush — no exception means pass


def test_record_failure_with_exception(fresh_recorder):
    try:
        raise ValueError("test error")
    except Exception as e:
        fresh_recorder.record_failure("test_category", e, {"key": "value"})
    metrics = fresh_recorder.get_metrics()
    assert metrics["failed_requests"] == 1


def test_record_self_test_failure(fresh_recorder):
    fresh_recorder.record_self_test_failure(
        test_name="chain_integrity",
        cell="event_bus",
        reason="hash mismatch",
    )


def test_get_metrics_structure(fresh_recorder):
    metrics = fresh_recorder.get_metrics()
    assert "active_requests" in metrics
    assert "avg_latency_ms" in metrics
    assert "total_tool_calls" in metrics
    assert "failed_requests" in metrics
    assert "running_cells" in metrics
    assert "request_count" in metrics


def test_begin_end_request(fresh_recorder):
    fresh_recorder.begin_request("TRACE-001")
    assert fresh_recorder.get_metrics()["active_requests"] == 1
    fresh_recorder.end_request("TRACE-001")
    assert fresh_recorder.get_metrics()["active_requests"] == 0


def test_update_cell_state(fresh_recorder):
    fresh_recorder.update_cell_state("mcp", "ACTIVE")
    assert fresh_recorder.get_metrics()["running_cells"]["mcp"] == "ACTIVE"


def test_loggers_actually_write_without_crashing():
    """Regression: %f in datefmt caused ValueError at runtime.
    This test forces an actual disk write through every logger."""
    import tempfile
    import os
    from pathlib import Path
    from kernel.observability.logger import _make_logger

    with tempfile.TemporaryDirectory() as tmp:
        from kernel import config
        original_dir = config.settings.observability_log_dir
        config.settings.observability_log_dir = Path(tmp)
        config.settings.observability_enabled = True
        try:
            tl = _make_logger("test_timeline", "test_timeline.log")
            mt = _make_logger("test_mcp", "test_mcp.log")
            ar = _make_logger("test_reasoning", "test_reasoning.log")
            pf = _make_logger("test_perf", "test_perf.log")
            fl = _make_logger("test_failure", "test_failure.log")

            tl.info("timeline_event | duration_ms=1.0")
            mt.info("mcp_event")
            ar.info("reasoning_event")
            pf.info("perf_event")
            fl.info("failure_event")

            # Force handler flush + close so file is written
            for logger in (tl, mt, ar, pf, fl):
                for h in logger.handlers:
                    h.flush()
                    h.close()

            # Verify files exist and are non-empty
            for name in ("test_timeline.log", "test_mcp.log", "test_reasoning.log",
                         "test_perf.log", "test_failure.log"):
                path = Path(tmp) / name
                assert path.exists(), f"{name} was not created"
                content = path.read_text(encoding="utf-8")
                assert len(content) > 0, f"{name} is empty"
                assert "|" in content, f"{name} missing expected format"
        finally:
            config.settings.observability_log_dir = original_dir
