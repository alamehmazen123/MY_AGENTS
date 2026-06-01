"""
cells/workspace/cell.py — WorkspaceCell
Jail invariant enforcement.
"""
from __future__ import annotations
from cells.base import BaseCell
from kernel.events import bus
from kernel.observability import recorder


class WorkspaceCell(BaseCell):
    """
    Workspace layer: safe file operations.
    Enforces: all file ops within workspace root.
    """
    
    def __init__(self):
        super().__init__("workspace")
        self._invariants = ["workspace_jailed"]
        self._guard = None
        self._transactions = None
        self._indexer = None
        self._rollback = None
    
    async def _on_init(self):
        from cells.workspace.guard import PathGuard
        from cells.workspace.transactions import TransactionManager
        from cells.workspace.indexer import IncrementalIndexer
        from cells.workspace.rollback import RollbackManager
        self._guard = PathGuard()
        self._transactions = TransactionManager()
        self._indexer = IncrementalIndexer()
        self._rollback = RollbackManager()
        recorder.update_cell_state(self.name, self.state.name)
        await bus.emit("cell.workspace.ready", {})
    
    async def read_file(self, path: str) -> dict:
        recorder.record_timeline("Workspace", "read_file")
        safe = self._guard.validate(path)
        if not safe:
            recorder.record_failure("workspace_path_escape", None, {"path": path})
            return {"error": "path_escape_attempt_blocked"}
        return {"content": safe.read_text(encoding="utf-8")}
    
    async def write_file(self, path: str, content: str) -> dict:
        recorder.record_timeline("Workspace", "write_file")
        safe = self._guard.validate(path)
        if not safe:
            recorder.record_failure("workspace_path_escape", None, {"path": path})
            return {"error": "path_escape_attempt_blocked"}
        return await self._transactions.write(safe, content)
    
    async def snapshot(self) -> dict:
        snap = await self._rollback.snapshot()
        return {"snapshot_id": snap}
    
    async def restore(self, snapshot_id: str) -> bool:
        return await self._rollback.restore(snapshot_id)
    
    async def _on_shutdown(self):
        recorder.update_cell_state(self.name, "offline")
        await bus.emit("cell.workspace.offline", {})
