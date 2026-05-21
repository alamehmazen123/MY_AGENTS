import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

def main():
    from kernel.mcp.runtime.worker_process import run_in_worker
    task = {'preset': 'workspace_indexer', 'args': {'action': 'index', 'path': '.'}}
    limits = {'memory_mb': 512, 'cpu_seconds': 30, 'open_files': 128, 'timeout': 60}
    start = time.time()
    result = run_in_worker(task, limits, 120)
    print('total duration:', time.time() - start)
    print(result)

if __name__ == '__main__':
    main()
