"""cells/mcp/presets/terminal_whitelist.py — Whitelisted shell commands."""
import subprocess
from pathlib import Path
from kernel.config import settings

ALLOWED_COMMANDS = {
    "ls", "dir", "pwd", "cd", "cat", "type", "head", "tail", "find", "grep",
    "git", "python", "python3", "node", "npm", "npx", "echo", "mkdir", "touch",
    "cp", "copy", "mv", "move", "rm", "del", "rmdir", "rd", "clear", "cls",
    "which", "where", "wc", "sort", "uniq", "diff", "date", "time", "whoami",
    "uname", "hostname", "curl", "wget", "code", "code.", "ollama",
}


def handle(args: dict) -> dict:
    command = args.get("command", "")
    if not command:
        return {"error": "missing_command"}
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return {"error": "empty_command"}
    base_cmd = cmd_parts[0].lower()
    if base_cmd not in ALLOWED_COMMANDS:
        return {"error": f"command_not_allowed: {base_cmd}"}
    cwd = args.get("cwd", str(settings.workspace_root))
    try:
        result = subprocess.run(
            cmd_parts, capture_output=True, text=True, timeout=30,
            cwd=Path(cwd).expanduser().resolve()
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "command_timeout"}
    except Exception as e:
        return {"error": str(e)}
