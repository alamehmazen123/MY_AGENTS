"""kernel/mcp/runtime/ipc.py — Inter-process communication for worker tasks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkerTask:
    preset: str
    args: dict[str, Any]


@dataclass
class WorkerResult:
    status: str  # "ok", "error", "killed", "timeout"
    data: dict[str, Any]
    error_message: str = ""
