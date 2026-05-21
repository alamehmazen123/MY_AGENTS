"""Test preset — sleeps for a configurable duration."""
import time

SCHEMA = {"name": "_test_sleep", "description": "Internal test preset.", "parameters": {}, "required": []}


def handle(args: dict) -> dict:
    duration = args.get("duration", 1)
    time.sleep(duration)
    return {"slept": duration}
