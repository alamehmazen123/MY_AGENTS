"""cells/mcp/presets/refactor_safe.py — Safe code refactoring (workspace-jailed)."""
import re
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "refactor_safe",
    "description": "Safe code refactoring like symbol renaming inside the workspace.",
    "parameters": {
        "action": {"type": "string", "enum": ["rename_symbol"]},
        "path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"},
    },
    "required": ["action", "path"],
}


def handle(args: dict) -> dict:
    action = args.get("action", "rename_symbol")
    path_str = args.get("path", "")
    if not path_str:
        return {"error": "missing_path"}
    try:
        p = _guard.validate(path_str)
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
        return {"error": "unknown_action"}
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}
