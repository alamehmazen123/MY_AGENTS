"""cells/mcp/presets/diff_engine.py — Generate unified diffs (workspace-jailed)."""
import difflib
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "diff_engine",
    "description": "Generate unified diffs between text or workspace files.",
    "parameters": {
        "action": {"type": "string", "enum": ["text", "files"]},
        "a": {"type": "string"}, "b": {"type": "string"},
        "path_a": {"type": "string"}, "path_b": {"type": "string"},
    },
    "required": ["action"],
}


def handle(args: dict) -> dict:
    action = args.get("action", "text")
    if action == "text":
        a = args.get("a", "")
        b = args.get("b", "")
        diff = list(difflib.unified_diff(
            a.splitlines(keepends=True), b.splitlines(keepends=True),
            fromfile="before", tofile="after"
        ))
        return {"diff": "".join(diff)}
    elif action == "files":
        path_a = args.get("path_a", "")
        path_b = args.get("path_b", "")
        if not path_a or not path_b:
            return {"error": "missing_paths"}
        try:
            p_a = _guard.validate(path_a)
            p_b = _guard.validate(path_b)
            a = p_a.read_text(encoding="utf-8", errors="replace")
            b = p_b.read_text(encoding="utf-8", errors="replace")
            diff = list(difflib.unified_diff(
                a.splitlines(keepends=True), b.splitlines(keepends=True),
                fromfile=p_a.name, tofile=p_b.name
            ))
            return {"diff": "".join(diff), "path_a": str(p_a), "path_b": str(p_b)}
        except WorkspaceViolation as e:
            return {"error": "workspace_violation", "message": str(e)}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "unknown_action"}
