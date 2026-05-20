"""cells/mcp/presets/refactor_safe.py — Safe code refactoring."""
import re
from pathlib import Path
from kernel.config import settings


def handle(args: dict) -> dict:
    action = args.get("action", "rename_symbol")
    path_str = args.get("path", "")
    if not path_str:
        return {"error": "missing_path"}
    try:
        p = Path(path_str).expanduser().resolve()
        workspace = settings.workspace_root.expanduser().resolve()
        if not (str(p).startswith(str(workspace)) or str(p).startswith(str(Path.home()))):
            return {"error": "path_not_allowed"}
        if not p.exists() or not p.is_file():
            return {"error": "file_not_found"}
        content = p.read_text(encoding="utf-8", errors="replace")

        if action == "rename_symbol":
            old = args.get("old", "")
            new = args.get("new", "")
            if not old or not new:
                return {"error": "missing_old_or_new"}
            pattern = r'\b' + re.escape(old) + r'\b'
            new_content = re.sub(pattern, new, content)
            p.write_text(new_content, encoding="utf-8")
            count = len(re.findall(pattern, content))
            return {"path": str(p), "replacements": count, "old": old, "new": new}
        else:
            return {"error": "unknown_action"}
    except Exception as e:
        return {"error": str(e)}
