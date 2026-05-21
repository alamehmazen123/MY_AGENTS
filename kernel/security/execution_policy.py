"""kernel/security/execution_policy.py — Single source of truth for execution permissions."""
from dataclasses import dataclass, field
from typing import Set
from .resource_limits import ResourceLimits


@dataclass(frozen=True)
class ExecutionPolicy:
    """Policy-driven execution permissions. Every tool is scoped by this."""
    allow_filesystem: bool = False
    allow_network: bool = False
    allow_subprocess: bool = False
    allow_shell: bool = False
    allow_git: bool = False
    allowed_paths: Set[str] = field(default_factory=set)
    limits: ResourceLimits = field(default_factory=ResourceLimits)

    def check_filesystem(self):
        if not self.allow_filesystem:
            raise PermissionError("filesystem_access_denied")

    def check_network(self):
        if not self.allow_network:
            raise PermissionError("network_access_denied")

    def check_subprocess(self):
        if not self.allow_subprocess:
            raise PermissionError("subprocess_access_denied")

    def check_shell(self):
        if not self.allow_shell:
            raise PermissionError("shell_access_denied")

    def check_git(self):
        if not self.allow_git:
            raise PermissionError("git_access_denied")
