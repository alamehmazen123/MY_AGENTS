"""Current date/time and timezone conversion (no network)."""
from datetime import datetime, timezone

SCHEMA = {
    "name": "clock",
    "description": "Current date/time, optionally in a given IANA timezone (e.g. Asia/Tokyo).",
    "parameters": {"timezone": {"type": "string"}},
    "required": [],
}


def handle(args: dict) -> dict:
    tz = args.get("timezone") or args.get("tz")
    try:
        if tz:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(tz))
        else:
            now = datetime.now(timezone.utc).astimezone()
        return {
            "iso": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "timezone": str(now.tzinfo),
            "unix": int(now.timestamp()),
        }
    except Exception as e:
        return {"error": str(e), "timezone": tz}
