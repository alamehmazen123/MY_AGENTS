"""kernel/security/workspace_guard.py — Real workspace jail with path traversal defense."""
from pathlib import Path
from typing import Optional


class WorkspaceViolation(Exception):
    """Raised when a path escapes the workspace jail."""
    pass


class WorkspaceGuard:
    """
    Enforce that ALL filesystem operations stay within a designated root.
    Resolves symlinks and prevents ../ escape, absolute path injection,
    and network share traversal.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()

    def validate(self, path: str | Path) -> Path:
        """
        Resolve *path* and ensure it lies inside self.root.
        Raises WorkspaceViolation on escape.
        """
        if not path:
            raise WorkspaceViolation("empty_path")

        p = Path(path).expanduser()

        # Reject absolute paths that point outside root
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self.root / p).resolve()

        # Follow symlinks and re-resolve
        try:
            resolved = resolved.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            raise WorkspaceViolation(f"unresolvable_path: {e}")

        # Ensure resolved is *within* root using relative_to
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise WorkspaceViolation(
                f"path_escape: {resolved} is outside workspace {self.root}"
            )

        return resolved

    def is_allowed(self, path: str | Path) -> bool:
        try:
            self.validate(path)
            return True
        except WorkspaceViolation:
            return False
