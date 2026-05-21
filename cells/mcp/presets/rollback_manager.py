"""cells/mcp/presets/rollback_manager.py — File snapshots and restore."""
import shutil
import time
from pathlib import Path

_SNAPSHOTS = {}


def handle(args: dict) -> dict:
    action = args.get("action", "snapshot")
    path_str = args.get("path", "")
    if not path_str:
        return {"error": "missing_path"}
    try:
        p = Path(path_str).expanduser().resolve()

        if action == "snapshot":
            snap_id = f"{p.name}_{int(time.time())}"
            backup = p.parent / f".rollback_{snap_id}"
            if p.is_dir():
                shutil.copytree(p, backup)
            else:
                shutil.copy2(p, backup)
            _SNAPSHOTS[snap_id] = str(backup)
            return {"snapshot_id": snap_id, "path": str(p)}

        elif action == "restore":
            snap_id = args.get("snapshot_id", "")
            backup_path = _SNAPSHOTS.get(snap_id)
            if not backup_path:
                return {"error": "snapshot_not_found"}
            bp = Path(backup_path)
            if bp.exists():
                if p.exists():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                if bp.is_dir():
                    shutil.copytree(bp, p)
                else:
                    shutil.copy2(bp, p)
                return {"restored": str(p), "snapshot_id": snap_id}
            return {"error": "backup_missing"}

        elif action == "list":
            snaps = [{"id": k, "path": v} for k, v in _SNAPSHOTS.items()]
            return {"snapshots": snaps}

        else:
            return {"error": "unknown_action"}
    except Exception as e:
        return {"error": str(e)}
