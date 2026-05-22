"""cells/mcp/cell.py — Production-grade MCPCell with real process isolation."""
from __future__ import annotations
import time
from cells.base import BaseCell
from kernel.events import bus
from kernel.config import settings
from kernel.security.workspace_guard import WorkspaceGuard
from kernel.security.resource_limits import ResourceLimits
from kernel.mcp.protocol.tool_definition import ToolCapability
from kernel.mcp.runtime.execution_pool import ExecutionPool
from kernel.telemetry.metrics import TelemetryCollector
from .registry import MCPRegistry
from .supervisor import MCPSupervisor


class MCPCell(BaseCell):
    """
    MCP layer: real process isolation, workspace jail, resource caps,
    schema-driven tools, and telemetry.
    """

    def __init__(self):
        super().__init__("mcp")
        self._invariants = [
            "memory_bounded",
            "workspace_jailed",
            "process_isolated",
            "policy_driven",
        ]
        self._registry = None
        self._pool = None
        self._supervisor = None
        self._telemetry = None
        self._guard = None
        self._guard_cache: dict[str, WorkspaceGuard] = {}

    async def _on_init(self):
        self._guard = WorkspaceGuard(settings.workspace_root)
        self._registry = MCPRegistry()
        self._pool = ExecutionPool(max_parallel=4)
        self._supervisor = MCPSupervisor()
        self._telemetry = TelemetryCollector()

        await self._load_presets()
        await self._supervisor.start()
        await bus.emit("cell.mcp.ready", {"presets_loaded": len(self._registry.list_tools())})

    async def _load_presets(self):
        import importlib

        presets = [
            ("file_explorer", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=512, timeout=30)),
            ("code_analyzer", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=256, timeout=15)),
            ("git_mcp", {ToolCapability.GIT, ToolCapability.SUBPROCESS}, ResourceLimits(memory_mb=256, timeout=30)),
            ("search_ripgrep", {ToolCapability.FILESYSTEM, ToolCapability.SUBPROCESS}, ResourceLimits(memory_mb=1024, timeout=60)),
            ("python_exec", {ToolCapability.PYTHON_EXEC}, ResourceLimits(memory_mb=512, timeout=30)),
            ("terminal_whitelist", set(), ResourceLimits(memory_mb=128, timeout=30)),  # disabled — replaced by structured
            ("diff_engine", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=256, timeout=15)),
            ("refactor_safe", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=256, timeout=15)),
            ("doc_generator", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=256, timeout=15)),
            ("dependency_inspector", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=256, timeout=15)),
            ("workspace_indexer", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=512, timeout=60)),
            ("health_monitor", set(), ResourceLimits(memory_mb=128, timeout=10)),
            ("project_scaffold", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=256, timeout=15)),
            ("rollback_manager", {ToolCapability.FILESYSTEM}, ResourceLimits(memory_mb=512, timeout=30)),
            ("structured_terminal", {ToolCapability.SUBPROCESS}, ResourceLimits(memory_mb=256, timeout=30)),
        ]

        for name, caps, limits in presets:
            try:
                mod = importlib.import_module(f"cells.mcp.presets.{name}")
                handler = getattr(mod, "handle", None)
                self._registry.register_preset(
                    name=name,
                    description=getattr(mod, "__doc__", ""),
                    handler=handler,
                    capabilities=caps,
                    limits=limits,
                    timeout=limits.timeout,
                )
            except Exception as e:
                print(f"[mcp] Failed to load preset {name}: {e}")

    def _guard_for(self, workspace: str | None) -> WorkspaceGuard:
        """Return a guard rooted at *workspace* (the user-selected folder) if it
        exists, else the default project-root guard. Guards are cached by path."""
        if not workspace:
            return self._guard
        from pathlib import Path
        try:
            root = Path(workspace).expanduser().resolve()
            if not root.is_dir():
                return self._guard
        except Exception:
            return self._guard
        key = str(root)
        if key not in self._guard_cache:
            self._guard_cache[key] = WorkspaceGuard(root)
        return self._guard_cache[key]

    async def invoke(self, preset: str, args: dict, workspace: str | None = None) -> dict:
        if not self._registry.has(preset):
            return {"error": "preset_not_found"}

        tool = self._registry.get(preset)
        if tool is None:
            return {"error": "preset_load_failed", "preset": preset}

        start = time.time()
        self._supervisor.heartbeat(preset)

        # Enforce workspace jail on filesystem tools, rooted at the user's
        # selected folder when provided (so agents work where the user is).
        guard = self._guard_for(workspace)
        if ToolCapability.FILESYSTEM in tool.capabilities:
            args = self._jail_args(args, guard)

        result = await self._pool.execute(tool, args, workspace=str(guard.root))

        duration = time.time() - start
        status = result.get("status", "error")
        self._supervisor.record(preset, status)
        self._telemetry.record(preset, duration, status)

        return result

    def _jail_args(self, args: dict, guard: WorkspaceGuard | None = None) -> dict:
        """Rewrite path arguments to stay inside the workspace jail."""
        guard = guard or self._guard
        jailed = dict(args)
        for key in ("path", "dest", "path_a", "path_b", "cwd"):
            if key in jailed and isinstance(jailed[key], str):
                try:
                    jailed[key] = str(guard.validate(jailed[key]))
                except Exception:
                    pass  # Let the preset report the violation
        return jailed

    def get_metrics(self) -> dict:
        return {
            "telemetry": self._telemetry.summary(),
            "executor": self._pool.metrics(),
            "supervisor": self._supervisor.summary(),
        }

    def list_tools(self) -> list[dict]:
        return self._registry.list_tools()

    async def _on_shutdown(self):
        await self._supervisor.shutdown()
        await bus.emit("cell.mcp.offline", {})
