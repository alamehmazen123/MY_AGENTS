"""cells/mcp/presets/workspace_indexer.py — Index workspace files."""
from pathlib import Path
from kernel.config import settings


def handle(args: dict) -> dict:
    path_str = args.get("path", str(settings.workspace_root))
    try:
        p = Path(path_str).expanduser().resolve()
        workspace = settings.workspace_root.expanduser().resolve()
        if not (str(p).startswith(str(workspace)) or str(p).startswith(str(Path.home()))):
            return {"error": "path_not_allowed"}
        if not p.exists() or not p.is_dir():
            return {"error": "not_a_directory"}

        index = []
        for item in p.rglob("*"):
            if item.is_file():
                rel = item.relative_to(p)
                parts = rel.parts
                # Skip hidden and common cache dirs
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
    except Exception as e:
        return {"error": str(e)}
