"""Persistent key-value memory for agents — survives across prompts and restarts."""
import json
from kernel.config import settings

_FILE = settings.data_dir / "agent_memory.json"

SCHEMA = {
    "name": "memory",
    "description": "Store/recall facts across prompts. actions: set, get, list, delete, all.",
    "parameters": {
        "action": {"type": "string", "enum": ["set", "get", "list", "delete", "all"]},
        "key": {"type": "string"}, "value": {"type": "string"},
    },
    "required": ["action"],
}


def _load() -> dict:
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict):
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def handle(args: dict) -> dict:
    action = args.get("action", "get")
    key = args.get("key")
    value = args.get("value")
    try:
        mem = _load()
        if action == "set":
            if not key:
                return {"error": "missing_key"}
            mem[key] = value
            _save(mem)
            return {"saved": key, "value": value}
        if action == "get":
            if not key:
                return {"error": "missing_key"}
            return {"key": key, "value": mem.get(key), "found": key in mem}
        if action == "list":
            return {"keys": list(mem.keys()), "count": len(mem)}
        if action == "delete":
            existed = key in mem
            mem.pop(key, None)
            _save(mem)
            return {"deleted": key, "existed": existed}
        if action == "all":
            return {"memory": mem, "count": len(mem)}
        return {"error": "unknown_action", "action": action}
    except Exception as e:
        return {"error": str(e)}
