"""
cells/runtime/thermal_monitor.py — Graduated Thermal Response
"""
import random
from typing import Dict
from kernel.config import settings


class ThermalMonitor:
    """Thermal zoning with proactive throttling."""
    
    def __init__(self):
        self._current_temp = 45.0  # Placeholder: real system reads sensors
        self._zone = "green"
    
    def read(self) -> float:
        # Placeholder: real implementation reads nvidia-smi or similar
        self._current_temp = 45.0 + random.random() * 10
        return self._current_temp
    
    def over_threshold(self) -> bool:
        return self.read() > settings.thermal_threshold_c
    
    def zone(self) -> str:
        t = self.read()
        if t < 60:
            return "green"
        elif t < settings.thermal_threshold_c:
            return "yellow"
        elif t < 95:
            return "red"
        return "critical"
    
    def recommended_action(self) -> str:
        z = self.zone()
        return {
            "green": "none",
            "yellow": "increase_token_interval",
            "red": "reduce_context_window",
            "critical": "emergency_unload",
        }.get(z, "none")
