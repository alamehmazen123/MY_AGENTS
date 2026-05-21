"""tests/security/test_workspace_jail.py — Workspace jail escape scenarios."""
import pytest
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation


class TestWorkspaceJail:
    @pytest.fixture
    def guard(self, tmp_path):
        return WorkspaceGuard(tmp_path)

    def test_valid_relative_path(self, guard, tmp_path):
        p = guard.validate("src/main.py")
        assert p == tmp_path / "src" / "main.py"

    def test_valid_nested_path(self, guard, tmp_path):
        p = guard.validate("a/b/c.txt")
        assert p == tmp_path / "a" / "b" / "c.txt"

    def test_rejects_dotdot_escape(self, guard):
        with pytest.raises(WorkspaceViolation):
            guard.validate("../secret.txt")

    def test_rejects_deep_dotdot_escape(self, guard):
        with pytest.raises(WorkspaceViolation):
            guard.validate("a/../../secret.txt")

    def test_rejects_absolute_outside(self, guard, tmp_path):
        outside = Path("/tmp/outside.txt") if __import__("sys").platform != "win32" else Path("C:/Windows/outside.txt")
        with pytest.raises(WorkspaceViolation):
            guard.validate(str(outside))

    def test_rejects_empty_path(self, guard):
        with pytest.raises(WorkspaceViolation):
            guard.validate("")

    def test_rejects_dotdot_prefix(self, guard):
        with pytest.raises(WorkspaceViolation):
            guard.validate("../")

    def test_rejects_symlink_escape_attempt(self, guard, tmp_path):
        import sys, os
        if sys.platform == "win32" and not hasattr(os, "symlink"):
            pytest.skip("symlinks not supported on this Windows configuration")
        # Create a symlink pointing outside
        outside = tmp_path.parent / "outside.txt"
        outside.write_text("secret")
        link = tmp_path / "link.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlink creation requires elevated privileges on Windows")
        with pytest.raises(WorkspaceViolation):
            guard.validate("link.txt")

    def test_is_allowed_returns_false_on_escape(self, guard):
        assert guard.is_allowed("../escape") is False

    def test_is_allowed_returns_true_on_valid(self, guard):
        assert guard.is_allowed("valid.txt") is True
