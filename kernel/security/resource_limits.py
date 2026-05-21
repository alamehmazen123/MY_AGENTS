"""kernel/security/resource_limits.py — Resource caps for worker processes."""
from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class ResourceLimits:
    memory_mb: int = 512
    cpu_seconds: float = 30.0
    open_files: int = 128
    timeout: float = 60.0
    max_output_bytes: int = 2 * 1024 * 1024

    def apply_to_process(self):
        """Apply limits to the current process (Linux/macOS)."""
        if sys.platform == "win32":
            return  # Windows uses Job Objects externally
        try:
            import resource
            resource.setrlimit(
                resource.RLIMIT_AS,
                (self.memory_mb * 1024 * 1024, resource.RLIM_INFINITY),
            )
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (int(self.cpu_seconds), resource.RLIM_INFINITY),
            )
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self.open_files, resource.RLIM_INFINITY),
            )
        except (ImportError, ValueError, OSError):
            pass
