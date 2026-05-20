"""
cells/evolution/catalog.py — Pre-Computed Patch Library
Parameterized templates. No generation at runtime.
"""
from typing import Dict, List, Any

PATCH_LIBRARY: List[Dict[str, Any]] = [
    {"id": "p1", "name": "reduce_context_window", "scenario": "high_memory", "metric": "ram_mb", "threshold": 16384, "params": {"window_ratio": 0.5}},
    {"id": "p2", "name": "increase_token_interval", "scenario": "thermal_spike", "metric": "gpu_temp_c", "threshold": 85, "params": {"interval_ms": 100}},
    {"id": "p3", "name": "emergency_unload", "scenario": "critical", "metric": "ram_mb", "threshold": 32768, "params": {}},
    {"id": "p4", "name": "disable_evolution", "scenario": "high_memory", "metric": "ram_mb", "threshold": 16384, "params": {}},
    {"id": "p5", "name": "queue_throttle", "scenario": "queue_flood", "metric": "queue_depth", "threshold": 100, "params": {"max_depth": 50}},
    {"id": "p6", "name": "stream_compress", "scenario": "snapshot_large", "metric": "snapshot_mb", "threshold": 500, "params": {"level": 6}},
    {"id": "p7", "name": "ghost_mode", "scenario": "critical", "metric": "gpu_temp_c", "threshold": 90, "params": {}},
    {"id": "p8", "name": "index_prune", "scenario": "index_rebuild", "metric": "index_time_ms", "threshold": 10000, "params": {"keep_recent": 1000}},
    {"id": "p9", "name": "batch_events", "scenario": "event_replay", "metric": "event_count", "threshold": 100000, "params": {"batch_size": 500}},
    {"id": "p10", "name": "limit_mcp", "scenario": "mcp_spawn", "metric": "mcp_count", "threshold": 50, "params": {"max_mcp": 30}},
]


class PatchCatalog:
    """Pre-computed patch library."""
    
    def __init__(self):
        self._patches = {p["id"]: p for p in PATCH_LIBRARY}
    
    def query(self, scenario: str, metric: str, threshold: float) -> List[Dict]:
        return [
            p for p in self._patches.values()
            if p["scenario"] == scenario and p["metric"] == metric and p["threshold"] <= threshold
        ]
    
    def get(self, patch_id: str) -> Dict:
        return self._patches.get(patch_id)
    
    @property
    def size(self) -> int:
        return len(self._patches)
