import sys
import threading
import time
import multiprocessing
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

def count_threads(label):
    threads = threading.enumerate()
    sys.stderr.write(f"[{label}] threads={len(threads)}: {[t.name for t in threads]}\n")
    sys.stderr.flush()

def _worker_debug(task_json, result_queue, limits_dict):
    count_threads("worker_start")
    import importlib
    preset = task_json["preset"]
    module_name = f"cells.mcp.presets.{preset}"
    sys.stderr.write(f"[worker] about to import {module_name}\n")
    sys.stderr.flush()
    mod = importlib.import_module(module_name)
    sys.stderr.write(f"[worker] imported {module_name}\n")
    sys.stderr.flush()
    count_threads("after_import")
    handler = getattr(mod, "handle", None)
    result = handler(task_json["args"])
    count_threads("after_handler")
    result_queue.put({"status": "ok", "data": result, "error_message": ""})
    count_threads("after_queue_put")
    sys.stderr.write("[worker] returning from _worker_debug\n")
    sys.stderr.flush()

def main():
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    task = {"preset": "workspace_indexer", "args": {"action": "index", "path": "."}}
    limits = {"memory_mb": 512, "cpu_seconds": 30, "open_files": 128, "timeout": 60}
    
    proc = ctx.Process(target=_worker_debug, args=(task, result_queue, limits))
    proc.start()
    proc.join(timeout=60)
    sys.stderr.write(f"[parent] alive={proc.is_alive()}\n")
    sys.stderr.flush()
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2)
        print("KILLED")
    else:
        try:
            result = result_queue.get(timeout=1)
            print("RESULT:", result.get("status"))
        except Exception as e:
            print("QUEUE ERROR:", e)

if __name__ == '__main__':
    main()
