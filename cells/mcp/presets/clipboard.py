"""Read from or write to the system clipboard."""
import subprocess
import sys

SCHEMA = {
    "name": "clipboard",
    "description": "Read or write the OS clipboard. actions: read, write (with 'text').",
    "parameters": {"action": {"type": "string", "enum": ["read", "write"]}, "text": {"type": "string"}},
    "required": ["action"],
}


def handle(args: dict) -> dict:
    action = args.get("action", "read")
    text = args.get("text", "")
    try:
        if sys.platform == "win32":
            if action == "read":
                out = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                                     capture_output=True, text=True, timeout=10)
                return {"text": out.stdout.replace("\r\n", "\n").rstrip("\n")}
            subprocess.run("clip", input=text, text=True, timeout=10, shell=True)
            return {"written": True, "chars": len(text)}
        # macOS / Linux
        if action == "read":
            cmd = ["pbpaste"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard", "-o"]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return {"text": out.stdout}
        cmd = ["pbcopy"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard"]
        subprocess.run(cmd, input=text, text=True, timeout=10)
        return {"written": True, "chars": len(text)}
    except Exception as e:
        return {"error": str(e)}
