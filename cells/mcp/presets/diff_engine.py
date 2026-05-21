"""cells/mcp/presets/diff_engine.py — Generate unified diffs."""
import difflib
from pathlib import Path


def handle(args: dict) -> dict:
    action = args.get("action", "text")
    if action == "text":
        a = args.get("a", "")
        b = args.get("b", "")
        diff = list(difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile="before", tofile="after"
        ))
        return {"diff": "".join(diff)}
    elif action == "files":
        path_a = args.get("path_a", "")
        path_b = args.get("path_b", "")
        if not path_a or not path_b:
            return {"error": "missing_paths"}
        try:
            p_a = Path(path_a).expanduser().resolve()
            p_b = Path(path_b).expanduser().resolve()
            a = p_a.read_text(encoding="utf-8", errors="replace")
            b = p_b.read_text(encoding="utf-8", errors="replace")
            diff = list(difflib.unified_diff(
                a.splitlines(keepends=True),
                b.splitlines(keepends=True),
                fromfile=p_a.name, tofile=p_b.name
            ))
            return {"diff": "".join(diff), "path_a": str(p_a), "path_b": str(p_b)}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "unknown_action"}
