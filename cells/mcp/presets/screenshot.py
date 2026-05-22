"""Capture a screenshot of the screen and save it as a PNG (mss)."""
import os
import time

SCHEMA = {
    "name": "screenshot",
    "description": "Capture the screen to a PNG file. Optional 'path' to choose where.",
    "parameters": {"path": {"type": "string"}},
    "required": [],
}


def handle(args: dict) -> dict:
    try:
        import mss
        from kernel.config import settings
        out = args.get("path") or str(settings.data_dir / f"screenshot_{int(time.time())}.png")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with mss.mss() as sct:
            sct.shot(mon=-1, output=out)
        return {"saved": out, "size_bytes": os.path.getsize(out)}
    except Exception as e:
        return {"error": str(e)}
