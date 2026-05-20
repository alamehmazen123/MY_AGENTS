"""cells/mcp/presets/search_ripgrep.py — Search files with ripgrep or Python fallback."""
import os
import re
import subprocess
from pathlib import Path
from kernel.config import settings


def handle(args: dict) -> dict:
    query = args.get("query", "")
    path_str = args.get("path", ".")
    if not query:
        return {"error": "missing_query"}
    try:
        p = Path(path_str).expanduser().resolve()
        workspace = settings.workspace_root.expanduser().resolve()
        if not (str(p).startswith(str(workspace)) or str(p).startswith(str(Path.home()))):
            return {"error": "path_not_allowed"}
        if not p.exists() or not p.is_dir():
            return {"error": "not_a_directory"}

        # Try ripgrep first
        try:
            result = subprocess.run(
                ["rg", "-n", "--no-heading", query, str(p)],
                capture_output=True, text=True, timeout=30
            )
            matches = []
            for line in result.stdout.splitlines():
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        matches.append({"file": parts[0], "line": int(parts[1]), "content": parts[2]})
            return {"matches": matches, "tool": "ripgrep", "count": len(matches)}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback to Python walk
        matches = []
        pattern = re.compile(re.escape(query))
        for root, _, files in os.walk(str(p)):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if pattern.search(line):
                            matches.append({"file": str(fpath), "line": i, "content": line})
                except Exception:
                    pass
        return {"matches": matches, "tool": "python_fallback", "count": len(matches)}
    except Exception as e:
        return {"error": str(e)}
