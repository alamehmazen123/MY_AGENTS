"""kernel/observability/dashboard.py — Metrics aggregation for the debug dashboard."""
from __future__ import annotations
from typing import List
from kernel.observability.recorder import recorder


def get_dashboard_metrics() -> dict:
    """Return current observability metrics for the dashboard."""
    return recorder.get_metrics()


def get_recent_traces(n: int = 50) -> List[dict]:
    """Return recent MCP tool calls as proxy traces."""
    return recorder.get_recent_traces(n)


def get_recent_failures(n: int = 50) -> List[dict]:
    """Return recent failures."""
    return recorder.get_recent_failures(n)
