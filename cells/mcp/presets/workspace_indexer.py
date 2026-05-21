"""cells/mcp/presets/workspace_indexer.py — Index workspace files (workspace-jailed)."""
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "workspace_indexer",
    "description": "Index all files in a workspace directory.",
    "parameters": {"path": {"type": "string"}},
    "required": [],
}


def handle(args: dict) -> dict:
    path_str = args.get("path", str(settings.workspace_root))
    try:
        p = _guard.validate(path_str)
        if not p.exists() or not p.is_dir():
            return {"error": "not_a_directory"}
        index = []
        for item in p.rglob("*"):
            if item.is_file():
                rel = item.relative_to(p)
                parts = rel.parts
                if any(part.startswith(".") for part in parts):
                    continue
                skip = {"node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
                if any(part in skip for part in parts):
                    continue
                try:
                    size = item.stat().st_size
                    index.append({"path": str(rel).replace("\\", "/"), "size": size})
                except Exception:
                    pass
        return {"path": str(p), "files": index, "count": len(index)}
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}
