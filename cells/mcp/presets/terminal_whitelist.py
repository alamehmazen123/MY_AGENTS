"""cells/mcp/presets/terminal_whitelist.py — DEPRECATED.
Raw shell execution is disabled. Use structured_terminal instead.
"""

SCHEMA = {
    "name": "terminal_whitelist",
    "description": "DEPRECATED — use structured_terminal instead.",
    "parameters": {},
    "required": [],
}


def handle(args: dict) -> dict:
    return {
        "error": "deprecated",
        "message": "terminal_whitelist is disabled for security. Use structured_terminal with structured commands instead."
    }
