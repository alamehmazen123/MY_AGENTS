"""Structured step-by-step reasoning scratchpad — persists thoughts between calls."""
import json
from kernel.config import settings

_FILE = settings.data_dir / "thoughts.json"

SCHEMA = {
    "name": "sequential_thinking",
    "description": "Record reasoning steps. actions: add (thought), list, clear.",
    "parameters": {
        "action": {"type": "string", "enum": ["add", "list", "clear"]},
        "thought": {"type": "string"},
    },
    "required": ["action"],
}


def _load() -> list:
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list):
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def handle(args: dict) -> dict:
    action = args.get("action", "list")
    try:
        items = _load()
        if action == "add":
            thought = args.get("thought", "")
            if not thought:
                return {"error": "missing_thought"}
            items.append({"step": len(items) + 1, "thought": thought})
            _save(items)
            return {"added_step": len(items), "total_steps": len(items)}
        if action == "list":
            return {"steps": items, "count": len(items)}
        if action == "clear":
            _save([])
            return {"cleared": True}
        return {"error": "unknown_action", "action": action}
    except Exception as e:
        return {"error": str(e)}
