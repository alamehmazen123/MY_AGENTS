"""
cells/mcp/cell.py — MCPCell
Genetic limits, lifecycle management.
"""
from __future__ import annotations
from cells.base import BaseCell
from kernel.events import bus


class MCPCell(BaseCell):
    """
    MCP layer: contained tools with sandboxing.
    """
    
    def __init__(self):
        super().__init__("mcp")
        self._invariants = ["memory_bounded", "workspace_jailed"]
        self._registry = None
        self._sandbox = None
        self._supervisor = None
    
    async def _on_init(self):
        from cells.mcp.registry import MCPRegistry
        from cells.mcp.sandbox import Sandbox
        from cells.mcp.supervisor import MCPSupervisor
        self._registry = MCPRegistry()
        self._sandbox = Sandbox()
        self._supervisor = MCPSupervisor()
        
        # Load 14 presets
        await self._load_presets()
        await bus.emit("cell.mcp.ready", {"presets_loaded": 14})
    
    async def _load_presets(self):
        presets = [
            "file_explorer", "code_analyzer", "git_mcp", "search_ripgrep",
            "python_exec", "terminal_whitelist", "diff_engine", "refactor_safe",
            "doc_generator", "dependency_inspector", "workspace_indexer",
            "health_monitor", "project_scaffold", "rollback_manager",
        ]
        for name in presets:
            self._registry.register_preset(name)
    
    async def invoke(self, preset: str, args: dict) -> dict:
        if not self._registry.has(preset):
            return {"error": "preset_not_found"}
        
        handler = self._registry.load(preset)
        if not handler:
            return {"error": "preset_load_failed", "preset": preset}
        
        # Sandbox execution
        result = await self._sandbox.run(preset, args, handler)
        self._supervisor.heartbeat(preset)
        return result
    
    async def _on_shutdown(self):
        await self._supervisor.shutdown()
        await bus.emit("cell.mcp.offline", {})
