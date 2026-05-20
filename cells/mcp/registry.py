"""
cells/mcp/registry.py — Lazy Loading, Dependency Resolution
"""
from typing import Dict, Any


class MCPRegistry:
    """Lazy-loaded MCP registry."""
    
    def __init__(self):
        self._presets: Dict[str, Any] = {}
    
    def register_preset(self, name: str):
        self._presets[name] = {"loaded": False, "module": f"cells.mcp.presets.{name}"}
    
    def has(self, name: str) -> bool:
        return name in self._presets
    
    def load(self, name: str) -> Any:
        p = self._presets.get(name)
        if not p:
            return None
        if not p["loaded"]:
            # Lazy import
            try:
                import importlib
                mod = importlib.import_module(p["module"])
                p["loaded"] = True
                p["handler"] = getattr(mod, "handle", None)
            except Exception:
                return None
        return p.get("handler")
