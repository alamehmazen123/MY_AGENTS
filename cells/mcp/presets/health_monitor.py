"""cells/mcp/presets/health_monitor.py — System resource monitoring."""
import os
import time

SCHEMA = {
    "name": "health_monitor",
    "description": "Monitor system CPU, memory, and disk usage.",
    "parameters": {},
    "required": [],
}


def handle(args: dict) -> dict:
    try:
        result = {
            "cpu_count": os.cpu_count(),
            "load_average": getattr(os, "getloadavg", lambda: None)(),
            "timestamp": time.time(),
        }
        try:
            import psutil
            mem = psutil.virtual_memory()
            result["memory"] = {"total": mem.total, "available": mem.available, "percent": mem.percent}
            disk = psutil.disk_usage(".")
            result["disk"] = {"total": disk.total, "used": disk.used, "free": disk.free, "percent": disk.percent}
        except ImportError:
            result["psutil"] = "not_installed"
        return result
    except Exception as e:
        return {"error": str(e)}
