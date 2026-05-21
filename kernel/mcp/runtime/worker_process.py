"""kernel/mcp/runtime/worker_process.py — Isolated worker that runs a single tool invocation."""
from __future__ import annotations
import sys
import traceback
import multiprocessing
from typing import Any


def _worker_main(task_json: dict, result_queue: multiprocessing.Queue, limits_dict: dict):
    """Entry point for the worker process."""
    import importlib
    from kernel.security.resource_limits import ResourceLimits

    limits = ResourceLimits(**limits_dict)
    limits.apply_to_process()

    preset = task_json["preset"]
    args = task_json["args"]

    try:
        module_name = f"cells.mcp.presets.{preset}"
        mod = importlib.import_module(module_name)
        handler = getattr(mod, "handle", None)
        if handler is None:
            result_queue.put({
                "status": "error",
                "data": {},
                "error_message": f"handler_not_found in {module_name}",
            })
            return
        result = handler(args)
        if not isinstance(result, dict):
            result = {"output": result}
        result_queue.put({"status": "ok", "data": result, "error_message": ""})
    except Exception as e:
        result_queue.put({
            "status": "error",
            "data": {},
            "error_message": f"{e}\n{traceback.format_exc()}",
        })


def run_in_worker(task_json: dict, limits_dict: dict, timeout: float) -> dict:
    """
    Spawn a fresh process, run the tool, enforce timeout, return result.
    """
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_worker_main, args=(task_json, result_queue, limits_dict))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2)
        return {"status": "killed", "data": {}, "error_message": "execution_timeout"}

    if proc.exitcode != 0:
        return {"status": "killed", "data": {}, "error_message": f"worker_exit_code_{proc.exitcode}"}

    try:
        return result_queue.get(timeout=1)
    except Exception:
        return {"status": "error", "data": {}, "error_message": "result_queue_empty"}
