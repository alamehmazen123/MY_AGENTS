"""kernel/telemetry/metrics.py — Capture tool invocation metrics."""
from __future__ import annotations
import time
from typing import Any
from collections import defaultdict


class TelemetryCollector:
    def __init__(self):
        self._invocations: list[dict] = []
        self._totals = defaultdict(int)

    def record(self, preset: str, duration: float, status: str, memory_mb: float | None = None):
        entry = {
            "preset": preset,
            "duration": duration,
            "status": status,
            "timestamp": time.time(),
            "memory_mb": memory_mb,
        }
        self._invocations.append(entry)
        self._totals[f"{preset}:{status}"] += 1
        self._totals["total"] += 1

    def summary(self) -> dict[str, Any]:
        if not self._invocations:
            return {"total": 0}
        total = len(self._invocations)
        errors = sum(1 for i in self._invocations if i["status"] != "ok")
        avg_duration = sum(i["duration"] for i in self._invocations) / total
        return {
            "total": total,
            "errors": errors,
            "avg_duration": round(avg_duration, 3),
            "by_preset": dict(self._totals),
        }

    def recent(self, n: int = 20) -> list[dict]:
        return self._invocations[-n:]
