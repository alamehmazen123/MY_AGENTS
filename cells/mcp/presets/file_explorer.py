"""cells/mcp/presets/file_explorer.py — Browse and read workspace files."""
from pathlib import Path
from kernel.config import settings


def _validate_path(path_str: str) -> tuple[Path | None, dict | None]:
    if not path_str:
        return None, {"error": "missing_path"}
    try:
        p = Path(path_str).expanduser().resolve()
        workspace = settings.workspace_root.expanduser().resolve()
        home = Path.home()
        allowed = str(p).startswith(str(workspace)) or str(p).startswith(str(home))
        if not allowed:
            return None, {"error": "path_not_allowed", "path": str(p)}
        return p, None
    except Exception as e:
        return None, {"error": str(e)}


def handle(args: dict) -> dict:
    action = args.get("action", "read")
    path_str = args.get("path", "")
    p, err = _validate_path(path_str)
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
                "path": str(p),
                "name": p.name,
                "type": "dir" if p.is_dir() else "file",
                "size": st.st_size if p.is_file() else None,
                "mtime": st.st_mtime,
            }

        else:
            return {"error": "unknown_action", "action": action}
    except Exception as e:
        return {"error": str(e), "path": str(p)}
