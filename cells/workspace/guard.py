"""
cells/workspace/guard.py — Path Validation, Chroot Jail
"""
from pathlib import Path
from typing import Optional
from kernel.config import settings


class PathGuard:
    """Prevent path traversal and enforce workspace jail."""
    
    def __init__(self, root: Optional[Path] = None):
        self.root = (root or settings.workspace_root).resolve()
    
    def validate(self, path: str) -> Optional[Path]:
        """Return resolved path if within jail, else None."""
        try:
            target = (self.root / path).resolve()
            # Ensure target is within root
            target.relative_to(self.root)
            return target
        except (ValueError, RuntimeError):
            return None
