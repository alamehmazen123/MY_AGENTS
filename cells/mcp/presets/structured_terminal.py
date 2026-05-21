"""cells/mcp/presets/structured_terminal.py — Structured commands, no raw shell (Phase 6)."""
import subprocess
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "structured_terminal",
    "description": "Execute structured whitelisted commands inside the workspace. No raw shell.",
    "parameters": {
        "command": {"type": "string", "enum": ["ls", "dir", "pwd", "cat", "head", "tail", "wc", "find", "mkdir", "rm", "cp", "mv"]},
        "path": {"type": "string"},
        "target": {"type": "string"},
        "dest": {"type": "string"},
        "lines": {"type": "integer"},
    },
    "required": ["command"],
}


def handle(args: dict) -> dict:
    cmd = args.get("command", "")
    path = args.get("path", ".")
    try:
        cwd = _guard.validate(path)
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}

    try:
        if cmd in ("ls", "dir"):
            result = subprocess.run(["dir", "/b"] if __import__("sys").platform == "win32" else ["ls", "-la"],
                                    capture_output=True, text=True, timeout=10, cwd=str(cwd))
            return {"stdout": result.stdout, "stderr": result.stderr}
        elif cmd == "pwd":
            return {"cwd": str(cwd)}
        elif cmd == "cat":
            target = Path(args.get("target", ""))
            t = _guard.validate(str(target))
            return {"content": t.read_text(encoding="utf-8", errors="replace")}
        elif cmd == "head":
            target = Path(args.get("target", ""))
            t = _guard.validate(str(target))
            lines = args.get("lines", 20)
            content = t.read_text(encoding="utf-8", errors="replace").splitlines()[:lines]
            return {"content": "\n".join(content)}
        elif cmd == "tail":
            target = Path(args.get("target", ""))
            t = _guard.validate(str(target))
            lines = args.get("lines", 20)
            content = t.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
            return {"content": "\n".join(content)}
        elif cmd == "wc":
            target = Path(args.get("target", ""))
            t = _guard.validate(str(target))
            text = t.read_text(encoding="utf-8", errors="replace")
            return {"lines": len(text.splitlines()), "words": len(text.split()), "chars": len(text)}
        elif cmd == "find":
            pattern = args.get("target", "*")
            matches = [str(p) for p in cwd.rglob(pattern) if p.is_file()]
            return {"matches": matches[:100], "count": len(matches)}
        elif cmd == "mkdir":
            target = Path(args.get("target", ""))
            t = _guard.validate(str(target))
            t.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(t)}
        elif cmd == "rm":
            target = Path(args.get("target", ""))
            t = _guard.validate(str(target))
            if t.is_dir():
                __import__("shutil").rmtree(t)
            else:
                t.unlink()
            return {"success": True, "path": str(t)}
        elif cmd == "cp":
            src = _guard.validate(args.get("target", ""))
            dest = _guard.validate(args.get("dest", ""))
            if src.is_dir():
                __import__("shutil").copytree(src, dest)
            else:
                __import__("shutil").copy2(src, dest)
            return {"success": True, "src": str(src), "dest": str(dest)}
        elif cmd == "mv":
            src = _guard.validate(args.get("target", ""))
            dest = _guard.validate(args.get("dest", ""))
            __import__("shutil").move(str(src), str(dest))
            return {"success": True, "src": str(src), "dest": str(dest)}
        else:
            return {"error": "unknown_command"}
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}
