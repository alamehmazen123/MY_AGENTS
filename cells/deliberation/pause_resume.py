"""
cells/deliberation/pause_resume.py — Checkpointing, Stream Buffer
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Checkpoint:
    iteration: int
    state: Dict[str, Any]
    stream_buffer: list[str] = field(default_factory=list)


class PauseResume:
    """Pause/resume with checkpointing every N tokens."""
    
    def __init__(self, checkpoint_every_tokens: int = 50):
        self._checkpoints: list[Checkpoint] = []
        self._stream_buffer: list[str] = []
        self._paused = False
        self._checkpoint_every = checkpoint_every_tokens
        self._token_count_since_checkpoint = 0
    
    def checkpoint(self, iteration: int, state: Dict[str, Any]):
        cp = Checkpoint(
            iteration=iteration,
            state=state.copy(),
            stream_buffer=self._stream_buffer.copy(),
        )
        self._checkpoints.append(cp)
        self._token_count_since_checkpoint = 0
    
    def append_stream(self, token: str):
        self._stream_buffer.append(token)
        self._token_count_since_checkpoint += 1
        if self._token_count_since_checkpoint >= self._checkpoint_every:
            # Trigger checkpoint via callback in real implementation
            pass
    
    def pause(self):
        self._paused = True
    
    def resume(self) -> Optional[Checkpoint]:
        self._paused = False
        if self._checkpoints:
            return self._checkpoints[-1]
        return None
    
    def latest_checkpoint(self) -> Optional[Checkpoint]:
        return self._checkpoints[-1] if self._checkpoints else None
    
    def is_paused(self) -> bool:
        return self._paused
