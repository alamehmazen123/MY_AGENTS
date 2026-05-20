"""
cells/evolution/human_gate.py — Final Approval UI Hook
"""
from typing import Dict, Any


class HumanGate:
    """UI hook for human approval of evolution patches."""
    
    def __init__(self):
        self._pending: Dict[str, Any] = {}
        self._auto_approve_env = False  # Set True only in testing
    
    async def approve(self, patch: Dict[str, Any]) -> bool:
        if self._auto_approve_env:
            return True
        
        # In production, this pushes to frontend and awaits response
        # For now, patches that don't modify kernel are auto-approved
        if patch.get("scenario") in ("high_memory", "thermal_spike", "queue_flood"):
            return True
        return False  # Requires explicit human approval
