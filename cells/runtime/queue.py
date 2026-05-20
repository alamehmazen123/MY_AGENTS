"""
cells/runtime/queue.py — Sprint Scheduler, User Priority
Bounded queue depth.
"""
from typing import Dict, List, Any
import uuid
import time
from collections import deque


class SprintQueue:
    """Bounded task queue with user priority."""
    
    def __init__(self, max_depth: int = 100):
        self.max_depth = max_depth
        self._queue: deque[Dict[str, Any]] = deque()
        self._tasks: Dict[str, Dict] = {}
        self._completed: List[str] = []
    
    async def enqueue(self, task: Dict[str, Any]) -> str:
        if len(self._queue) >= self.max_depth:
            raise RuntimeError("queue_depth_limit_exceeded")
        
        task_id = str(uuid.uuid4())
        entry = {
            "id": task_id,
            "prompt": task.get("prompt", ""),
            "model": task.get("model", "default"),
            "priority": task.get("priority", 0),
            "created_at": time.time(),
            "status": "queued",
        }
        self._tasks[task_id] = entry
        # Insert by priority (higher first)
        inserted = False
        for i, existing in enumerate(self._queue):
            if existing["priority"] < entry["priority"]:
                self._queue.insert(i, entry)
                inserted = True
                break
        if not inserted:
            self._queue.append(entry)
        return task_id
    
    def get(self, task_id: str) -> Dict:
        return self._tasks.get(task_id)
    
    def pop(self) -> Dict:
        return self._queue.popleft() if self._queue else {}
    
    def complete(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._completed.append(task_id)
    
    @property
    def depth(self) -> int:
        return len(self._queue)
    
    def status(self) -> Dict[str, Any]:
        return {
            "depth": self.depth,
            "max_depth": self.max_depth,
            "total_tasks": len(self._tasks),
            "completed": len(self._completed),
        }
