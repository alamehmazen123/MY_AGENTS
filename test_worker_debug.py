import sys
import time
import multiprocessing
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

def _worker_main_debug(task_json, result_queue, limits_dict):
    import sys
    sys.stderr.write("[worker] started\n")
    sys.stderr.flush()
    
    import importlib
    from kernel.security.resource_limits import ResourceLimits
    sys.stderr.write("[worker] imported ResourceLimits\n")
    sys.stderr.flush()
    
    limits = ResourceLimits(**limits_dict)
    limits.apply_to_process()
    sys.stderr.write("[worker] applied limits\n")
    sys.stderr.flush()
    
    preset = task_json["preset"]
    args = task_json["args"]
    sys.stderr.write(f"[worker] preset={preset} args={args}\n")
    sys.stderr.flush()
    
    try:
        module_name = f"cells.mcp.presets.{preset}"
        sys.stderr.write(f"[worker] importing {module_name}\n")
        sys.stderr.flush()
        mod = importlib.import_module(module_name)
        sys.stderr.write(f"[worker] imported {module_name}\n")
        sys.stderr.flush()
        handler = getattr(mod, "handle", None)
        if handler is None:
            result_queue.put({"status": "error", "data": {}, "error_message": f"handler_not_found in {module_name}"})
            return
        sys.stderr.write("[worker] calling handler\n")
        sys.stderr.flush()
        result = handler(args)
        sys.stderr.write(f"[worker] handler returned: {type(result)}\n")
        sys.stderr.flush()
        if not isinstance(result, dict):
            result = {"output": result}
        result_queue.put({"status": "ok", "data": result, "error_message": ""})
        sys.stderr.write("[worker] put result in queue\n")
        sys.stderr.flush()
    except Exception as e:
        import traceback
        result_queue.put({
            "status": "error",
            "data": {},
            "error_message": f"{e}\n{traceback.format_exc()}",
        })
        sys.stderr.write(f"[worker] exception: {e}\n")
        sys.stderr.flush()

def main():
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    task = {"preset": "workspace_indexer", "args": {"action": "index", "path": "."}}
    limits = {"memory_mb": 512, "cpu_seconds": 30, "open_files": 128, "timeout": 60}
    
    proc = ctx.Process(target=_worker_main_debug, args=(task, result_queue, limits))
    start = time.time()
    proc.start()
    sys.stderr.write(f"[parent] process started, pid={proc.pid}\n")
    sys.stderr.flush()
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
        try:
            result = result_queue.get(timeout=1)
            print("RESULT:", result)
        except Exception as e:
            print("QUEUE ERROR:", e)

if __name__ == '__main__':
    main()
