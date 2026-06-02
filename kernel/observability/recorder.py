"""kernel/observability/recorder.py — In-memory metrics + periodic flushing."""
from __future__ import annotations
import time
import traceback
import json
import threading
import random
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import deque

from kernel.observability.trace_context import get_trace_id
from kernel.observability.logger import (
    execution_timeline_logger,
    mcp_trace_logger,
    agent_reasoning_logger,
    performance_logger,
    failure_logger,
)
from kernel.config import settings


@dataclass
class PerformanceEntry:
    component: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class ObservabilityRecorder:
    """Central recorder for all observability events. Thread-safe."""

    def __init__(self):
        self._active_requests: set[str] = set()
        self._performance_history: deque[PerformanceEntry] = deque(
            maxlen=settings.observability_performance_window
        )
        self._failed_requests: deque[dict] = deque(maxlen=1000)
        self._tool_calls: deque[dict] = deque(maxlen=1000)
        self._request_count: int = 0
        self._running_cells: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._alert_webhook = settings.observability_alert_webhook

    def _should_sample(self) -> bool:
        """Check if current event should be sampled based on config."""
        rate = settings.observability_sample_rate
        if rate >= 1.0:
            return True
        if rate <= 0.0:
            return False
        return random.random() < rate

    async def _send_alert(self, category: str, message: str):
        """Best-effort alert dispatch to configured webhook."""
        if not self._alert_webhook:
            return
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    self._alert_webhook,
                    json={"category": category, "message": message, "timestamp": time.time()},
                )
        except Exception:
            pass  # Alerting must never break the main flow

    # ---- Phase A: Request trace -----------------------------------------

    def begin_request(self, trace_id: str):
        with self._lock:
            self._active_requests.add(trace_id)

    def end_request(self, trace_id: str):
        with self._lock:
            self._active_requests.discard(trace_id)

    # ---- Phase B: Execution timeline ------------------------------------

    def record_timeline(self, component: str, event: str, duration_ms: float = 0.0):
        if not settings.observability_enabled:
            return
        if not self._should_sample():
            return
        execution_timeline_logger.info(
            "%s | %s | duration_ms=%.3f", component, event, duration_ms
        )

    # ---- Phase C: MCP trace ---------------------------------------------

    def record_mcp_call(
        self,
        tool: str,
        args: dict,
        duration_ms: float,
        status: str,
        error: Optional[str] = None,
    ):
        if not settings.observability_enabled:
            return
        if not self._should_sample():
            return
        with self._lock:
            self._tool_calls.append(
                {
                    "tool": tool,
                    "args": args,
                    "duration_ms": duration_ms,
                    "status": status,
                    "timestamp": time.time(),
                }
            )
        extra = f" | error={error}" if error else ""
        mcp_trace_logger.info(
            "tool=%s | args=%s | duration_ms=%.3f | status=%s%s",
            tool,
            json.dumps(args, default=str),
            duration_ms,
            status,
            extra,
        )

    # ---- Phase D: Agent decision trace ----------------------------------

    def record_agent_reasoning(
        self,
        agent: str,
        prompt_length: int,
        model: str,
        tools_detected: int,
        tools_executed: int,
        response_length: int,
    ):
        if not settings.observability_enabled:
            return
        if not self._should_sample():
            return
        agent_reasoning_logger.info(
            "agent=%s | prompt_len=%d | model=%s | tools_detected=%d | tools_executed=%d | response_len=%d",
            agent,
            prompt_length,
            model,
            tools_detected,
            tools_executed,
            response_length,
        )

    # ---- Phase E: Performance trace -------------------------------------

    def record_performance(self, component: str, duration_ms: float):
        if not settings.observability_enabled:
            return
        if not self._should_sample():
            return
        with self._lock:
            self._performance_history.append(
                PerformanceEntry(component, duration_ms)
            )
            self._request_count += 1
            should_flush = (
                self._request_count % settings.observability_performance_window == 0
            )

        performance_logger.info("component=%s | duration_ms=%.3f", component, duration_ms)

        if should_flush:
            self._flush_averages()

    def _flush_averages(self):
        with self._lock:
            hist = list(self._performance_history)
        if not hist:
            return
        by_component: Dict[str, List[float]] = {}
        for entry in hist:
            by_component.setdefault(entry.component, []).append(entry.duration_ms)

        for component, values in by_component.items():
            avg = sum(values) / len(values)
            min_v = min(values)
            max_v = max(values)
            performance_logger.info(
                "AVERAGE_FLUSH component=%s | count=%d | avg_ms=%.3f | min_ms=%.3f | max_ms=%.3f",
                component,
                len(values),
                avg,
                min_v,
                max_v,
            )

    # ---- Phase F: Failure trace -----------------------------------------

    def record_failure(
        self,
        category: str,
        exception: Optional[BaseException] = None,
        context: Optional[dict] = None,
    ):
        if not settings.observability_enabled:
            return
        if not self._should_sample():
            return
        trace_id = get_trace_id()
        entry = {
            "trace_id": trace_id,
            "category": category,
            "context": context or {},
            "timestamp": time.time(),
        }
        stack = ""
        if exception:
            entry["exception_type"] = type(exception).__name__
            entry["exception_msg"] = str(exception)
            entry["stack_trace"] = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            stack = "".join(entry["stack_trace"])

        with self._lock:
            self._failed_requests.append(entry)

        failure_logger.error(
            "category=%s | trace_id=%s | context=%s\n%s",
            category,
            trace_id,
            json.dumps(context or {}, default=str),
            stack,
        )

        # Fire alerting webhook asynchronously (fire-and-forget)
        alert_msg = f"[{category}] {trace_id or 'NO_TRACE'}: {json.dumps(context or {}, default=str)}"
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_alert(category, alert_msg))
        except RuntimeError:
            # No event loop running — skip alerting in sync/test contexts
            pass

    # ---- Phase G: Self-test ---------------------------------------------

    def record_self_test_failure(
        self,
        test_name: str,
        cell: str,
        reason: str,
        exception: Optional[BaseException] = None,
    ):
        if not settings.observability_enabled:
            return
        stack = ""
        if exception:
            stack = "".join(
                traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
            )
        failure_logger.error(
            "SELF_TEST_FAILED test=%s | cell=%s | reason=%s\n%s",
            test_name,
            cell,
            reason,
            stack,
        )

    # ---- Phase H: Dashboard metrics -------------------------------------

    def get_metrics(self) -> dict:
        with self._lock:
            total_perf = len(self._performance_history)
            avg_latency = 0.0
            if total_perf > 0:
                avg_latency = sum(e.duration_ms for e in self._performance_history) / total_perf

            return {
                "active_requests": len(self._active_requests),
                "avg_latency_ms": round(avg_latency, 3),
                "total_tool_calls": len(self._tool_calls),
                "failed_requests": len(self._failed_requests),
                "running_cells": dict(self._running_cells),
                "request_count": self._request_count,
            }

    def update_cell_state(self, cell_name: str, state: str):
        with self._lock:
            self._running_cells[cell_name] = state

    def get_recent_traces(self, n: int = 50) -> List[dict]:
        with self._lock:
            return list(self._tool_calls)[-n:]

    def get_recent_failures(self, n: int = 50) -> List[dict]:
        with self._lock:
            return list(self._failed_requests)[-n:]

    def clear_recent_traces(self) -> None:
        with self._lock:
            self._tool_calls.clear()

    def clear_recent_failures(self) -> None:
        with self._lock:
            self._failed_requests.clear()


# Singleton ---------------------------------------------------------------
recorder = ObservabilityRecorder()
