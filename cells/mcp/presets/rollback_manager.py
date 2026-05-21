"""cells/mcp/presets/rollback_manager.py — File snapshots and restore (workspace-jailed)."""
import shutil
import time
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)
_SNAPSHOTS = {}

SCHEMA = {
    "name": "rollback_manager",
    "description": "Create and restore file snapshots inside the workspace.",
    "parameters": {
        "action": {"type": "string", "enum": ["snapshot", "restore", "list"]},
        "path": {"type": "string"},
        "snapshot_id": {"type": "string"},
    },
    "required": ["action", "path"],
}


def handle(args: dict) -> dict:
    action = args.get("action", "snapshot")
    path_str = args.get("path", "")
    if not path_str:
        return {"error": "missing_path"}
    try:
        p = _guard.validate(path_str)
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
        return {"error": "unknown_action"}
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}
