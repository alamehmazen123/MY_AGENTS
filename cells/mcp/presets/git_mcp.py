"""cells/mcp/presets/git_mcp.py — Structured Git operations (workspace-jailed)."""
import subprocess
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "git_mcp",
    "description": "Execute structured git commands inside the workspace.",
    "parameters": {
        "action": {"type": "string", "enum": ["status", "log", "diff", "branch", "show"]},
        "path": {"type": "string"},
        "n": {"type": "integer"},
        "ref": {"type": "string"},
    },
    "required": ["action"],
}


def _git_cmd(args: list, cwd: str | None = None) -> dict:
    try:
        result = subprocess.run(
            ["git"] + args, capture_output=True, text=True, timeout=30, cwd=cwd
        )
        return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except FileNotFoundError:
        return {"error": "git_not_found"}
    except subprocess.TimeoutExpired:
        return {"error": "git_command_timeout"}
    except Exception as e:
        return {"error": str(e)}


def handle(args: dict) -> dict:
    action = args.get("action", "status")
    path_str = args.get("path", str(settings.workspace_root))
    try:
        cwd = _guard.validate(path_str)
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}

    if action == "status":
        return _git_cmd(["status", "-sb"], str(cwd))
    elif action == "log":
        n = args.get("n", 10)
        return _git_cmd(["log", f"-n{n}", "--oneline"], str(cwd))
    elif action == "diff":
        return _git_cmd(["diff"], str(cwd))
    elif action == "branch":
        return _git_cmd(["branch", "-a"], str(cwd))
    elif action == "show":
        ref = args.get("ref", "HEAD")
        return _git_cmd(["show", "--stat", ref], str(cwd))
    else:
        return {"error": "unknown_action"}
