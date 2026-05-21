"""cells/mcp/presets/file_explorer.py — Browse, read, write, and manage workspace files."""
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "file_explorer",
    "description": "Browse, read, write, delete files and directories within the workspace.",
    "parameters": {
        "action": {"type": "string", "enum": ["read", "list", "stat", "write", "delete", "mkdir", "move"]},
        "path": {"type": "string"},
        "content": {"type": "string"},
        "dest": {"type": "string"},
    },
    "required": ["action", "path"],
}


def _resolve(path_str: str):
    try:
        return _guard.validate(path_str)
    except WorkspaceViolation as e:
        return None, {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return None, {"error": str(e)}


def handle(args: dict) -> dict:
    action = args.get("action", "read")
    path_str = args.get("path", "")
    p, err = _resolve(path_str)
    if err:
        return err

    try:
        if action == "read":
            if not p.exists():
                return {"error": "not_found", "path": str(p)}
            if p.is_dir():
                return {"error": "is_directory", "path": str(p)}
            MAX_SIZE = 2 * 1024 * 1024
            size = p.stat().st_size
            if size > MAX_SIZE:
                return {"error": "file_too_large", "path": str(p), "size": size}
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"content": content, "path": str(p), "name": p.name, "size": size}

        elif action == "list":
            if not p.exists() or not p.is_dir():
                return {"error": "not_a_directory", "path": str(p)}
            items = []
            for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                items.append({
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                })
            return {"items": items, "path": str(p)}

        elif action == "stat":
            if not p.exists():
                return {"error": "not_found", "path": str(p)}
            st = p.stat()
            return {
                "path": str(p), "name": p.name,
                "type": "dir" if p.is_dir() else "file",
                "size": st.st_size if p.is_file() else None,
                "mtime": st.st_mtime,
            }

        elif action == "write":
            content = args.get("content", "")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p), "bytes_written": len(content.encode("utf-8"))}

        elif action == "delete":
            if not p.exists():
                return {"error": "not_found", "path": str(p)}
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"success": True, "path": str(p)}

        elif action == "mkdir":
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(p)}

        elif action == "move":
            dest_str = args.get("dest", "")
            if not dest_str:
                return {"error": "missing_dest"}
            dest, derr = _resolve(dest_str)
            if derr:
                return derr
            import shutil
            shutil.move(str(p), str(dest))
            return {"success": True, "src": str(p), "dest": str(dest)}

        else:
            return {"error": "unknown_action", "action": action}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc(), "path": str(p)}
