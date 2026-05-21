"""kernel/telemetry/events.py — Lightweight event bus for telemetry."""
from __future__ import annotations
from typing import Callable


class EventBus:
    def __init__(self):
        self._handlers: list[Callable] = []

    def subscribe(self, handler: Callable):
        self._handlers.append(handler)

    def emit(self, event: str, data: dict):
        for h in self._handlers:
            try:
                h(event, data)
            except Exception:
                pass
