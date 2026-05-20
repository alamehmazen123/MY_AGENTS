"""
cells/runtime/stream_buffer.py — Token Buffering, Backpressure
"""
from typing import List, Optional
from collections import deque


class StreamBuffer:
    """Token buffer with backpressure and pause support."""
    
    def __init__(self, max_size: int = 4096):
        self.max_size = max_size
        self._buffer: deque[str] = deque()
        self._active = False
        self._paused = False
    
    def start(self):
        self._active = True
        self._buffer.clear()
    
    def end(self):
        self._active = False
    
    def push(self, token: str) -> bool:
        if not self._active or self._paused:
            return False
        if len(self._buffer) >= self.max_size:
            return False  # Backpressure
        self._buffer.append(token)
        return True
    
    def pop(self) -> Optional[str]:
        return self._buffer.popleft() if self._buffer else None
    
    def peek_all(self) -> List[str]:
        return list(self._buffer)
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    @property
    def size(self) -> int:
        return len(self._buffer)
