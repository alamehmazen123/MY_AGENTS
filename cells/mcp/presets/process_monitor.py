"""System health: CPU, memory, disk, and top processes (psutil)."""

SCHEMA = {
    "name": "process_monitor",
    "description": "Report CPU/memory/disk usage and the top memory-using processes.",
    "parameters": {"top": {"type": "integer"}},
    "required": [],
}


def handle(args: dict) -> dict:
    try:
        import psutil
        top = int(args.get("top", 5) or 5)
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                continue
        procs.sort(key=lambda x: (x.get("memory_percent") or 0), reverse=True)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.3),
            "cpu_count": psutil.cpu_count(),
            "memory": {"total": vm.total, "used": vm.used, "percent": vm.percent},
            "disk": {"total": disk.total, "used": disk.used, "percent": disk.percent},
            "top_processes": procs[:top],
        }
    except Exception as e:
        return {"error": str(e)}
