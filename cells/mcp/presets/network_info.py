"""cells/mcp/presets/network_info.py — Report this machine's local and public IP.

Replaces the need to "open CMD and run ipconfig": returns hostname, the local
LAN IP, and the public IP (via an external echo service).
"""
import socket
import urllib.request

SCHEMA = {
    "name": "network_info",
    "description": "Return this machine's hostname, local IP, and public IP address.",
    "parameters": {},
    "required": [],
}


def handle(args: dict) -> dict:
    info: dict = {}
    try:
        info["hostname"] = socket.gethostname()
    except Exception as e:
        info["hostname_error"] = str(e)

    # Local LAN IP — open a UDP socket to a public address (no packets sent).
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            info["local_ip"] = s.getsockname()[0]
        finally:
            s.close()
    except Exception as e:
        info["local_ip_error"] = str(e)

    # Public IP via an external echo service.
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=10) as resp:
            info["public_ip"] = resp.read().decode("utf-8", errors="replace").strip()
    except Exception as e:
        info["public_ip_error"] = str(e)

    return info
