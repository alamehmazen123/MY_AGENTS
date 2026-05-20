"""
cells/evolution/cell.py — EvolutionCell: Catalog-Based Patch Selection
Safe improvement without runtime generation.
"""
from __future__ import annotations
from cells.base import BaseCell, CellState
from kernel.events import bus


class EvolutionCell(BaseCell):
    """
    Evolution layer: safe improvement via pre-computed catalog.
    Zero runtime patch generation.
    """
    
    def __init__(self):
        super().__init__("evolution")
        self._invariants = ["evolution_reversible", "workspace_jailed"]
        self._catalog = None
        self._selector = None
        self._deployment = None
        self._human_gate = None
    
    async def _on_init(self):
        from cells.evolution.catalog import PatchCatalog
        from cells.evolution.pareto_selector import ParetoSelector
        from cells.evolution.deployment import DeploymentManager
        from cells.evolution.human_gate import HumanGate
        self._catalog = PatchCatalog()
        self._selector = ParetoSelector()
        self._deployment = DeploymentManager()
        self._human_gate = HumanGate()
        await bus.emit("cell.evolution.ready", {"catalog_size": self._catalog.size})
    
    async def propose(self, scenario: str, metric: str, threshold: float, weights: dict) -> dict:
        """Propose a patch from catalog. No generation."""
        candidates = self._catalog.query(scenario, metric, threshold)
        if not candidates:
            return {"status": "no_patch_available"}
        
        selected = self._selector.select(candidates, weights)
        return {
            "status": "proposed",
            "patch": selected,
            "requires_approval": True,
        }
    
    async def deploy(self, patch_id: str, auto_rollback: bool = True) -> dict:
        """Deploy a patch. Auto-rollback on anomaly."""
        patch = self._catalog.get(patch_id)
        if not patch:
            return {"status": "not_found"}
        
        # Human gate
        if not await self._human_gate.approve(patch):
            return {"status": "rejected_by_gate"}
        
        result = await self._deployment.deploy(patch)
        if result.get("anomaly") and auto_rollback:
            await self._deployment.rollback(patch)
            return {"status": "deployed_then_rolled_back", "reason": result["anomaly"]}
        
        return {"status": "deployed", "patch": patch_id}
    
    async def _on_shutdown(self):
        await bus.emit("cell.evolution.offline", {})
