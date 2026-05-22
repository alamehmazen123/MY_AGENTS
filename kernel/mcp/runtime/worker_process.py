"""kernel/mcp/runtime/worker_process.py — Isolated worker that runs a single tool invocation."""
from __future__ import annotations
import json
import os
import sys
import tempfile
import traceback
import multiprocessing
from typing import Any


def _worker_main(task_json: dict, result_path: str, limits_dict: dict):
    """Entry point for the worker process. Writes result JSON to result_path."""
    # Point the workspace jail at the user-selected folder BEFORE any kernel
    # module (and therefore kernel.config.settings) is imported, so presets that
    # build their guard from settings.workspace_root at import time pick it up.
    workspace = task_json.get("workspace")
    if workspace:
        os.environ["MY_AGENTS_WORKSPACE_ROOT"] = workspace

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
            result = {
                "status": "error",
                "data": {},
                "error_message": f"handler_not_found in {module_name}",
            }
        else:
            result = handler(args)
            if not isinstance(result, dict):
                result = {"output": result}
            result = {"status": "ok", "data": result, "error_message": ""}
    except Exception as e:
        result = {
            "status": "error",
            "data": {},
            "error_message": f"{e}\n{traceback.format_exc()}",
        }

    try:
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except Exception as e:
        # If we cannot write the result file, at least crash loudly in stderr
        sys.stderr.write(f"[worker] failed to write result file: {e}\n")
        sys.stderr.flush()


def run_in_worker(task_json: dict, limits_dict: dict, timeout: float) -> dict:
    """
    Spawn a fresh process, run the tool, enforce timeout, return result.
    Uses a temporary file for IPC to avoid Windows pipe-buffer deadlocks.
    """
    ctx = multiprocessing.get_context("spawn")
    fd, result_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    proc = ctx.Process(target=_worker_main, args=(task_json, result_path, limits_dict))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2)
        try:
            os.unlink(result_path)
        except OSError:
            pass
        return {"status": "killed", "data": {}, "error_message": "execution_timeout"}

    if proc.exitcode != 0:
        try:
            os.unlink(result_path)
        except OSError:
            pass
        return {"status": "killed", "data": {}, "error_message": f"worker_exit_code_{proc.exitcode}"}

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        result = {"status": "error", "data": {}, "error_message": f"result_file_read_failed: {e}"}
    finally:
        try:
            os.unlink(result_path)
        except OSError:
            pass

    return result
