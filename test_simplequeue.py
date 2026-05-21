import sys
import time
import multiprocessing
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

def _worker_debug(task_json, result_queue, limits_dict):
    import importlib
    preset = task_json["preset"]
    module_name = f"cells.mcp.presets.{preset}"
    mod = importlib.import_module(module_name)
    handler = getattr(mod, "handle", None)
    result = handler(task_json["args"])
    result_queue.put({"status": "ok", "data": result, "error_message": ""})

def main():
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.SimpleQueue()
    task = {"preset": "workspace_indexer", "args": {"action": "index", "path": "."}}
    limits = {"memory_mb": 512, "cpu_seconds": 30, "open_files": 128, "timeout": 60}
    
    proc = ctx.Process(target=_worker_debug, args=(task, result_queue, limits))
    start = time.time()
    proc.start()
    proc.join(timeout=60)
    elapsed = time.time() - start
    sys.stderr.write(f"[parent] join returned after {elapsed:.1f}s, alive={proc.is_alive()}\n")
    sys.stderr.flush()
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2)
        print("KILLED")
    else:
        result = result_queue.get()
        print("RESULT:", result.get("status"), "count:", result.get("data", {}).get("count"))

if __name__ == '__main__':
    main()
