"""
cells/gateway/protocol.py — Unified Message Schema (14 events)
"""
from typing import Dict, Any
from enum import Enum


class EventType(Enum):
    # System
    SYSTEM_ONLINE = "system.online"
    SYSTEM_OFFLINE = "system.offline"
    
    # Cell lifecycle
    CELL_READY = "cell.ready"
    CELL_DEGRADED = "cell.degraded"
    CELL_OFFLINE = "cell.offline"
    
    # Prompt
    PROMPT_SUBMIT = "prompt.submit"
    PROMPT_ACK = "prompt.ack"
    PROMPT_STREAM = "prompt.stream"
    PROMPT_COMPLETE = "prompt.complete"
    
    # Control
    PAUSE = "control.pause"
    RESUME = "control.resume"
    STOP = "control.stop"
    
    # Status
    STATUS_UPDATE = "status.update"


class Protocol:
    """Validate and construct protocol messages."""
    
    SCHEMA: Dict[str, Dict[str, Any]] = {
        EventType.PROMPT_SUBMIT.value: {"required": ["prompt", "model"], "optional": ["context", "priority"]},
        EventType.PROMPT_STREAM.value: {"required": ["task_id", "token"], "optional": []},
        EventType.PROMPT_COMPLETE.value: {"required": ["task_id"], "optional": ["result", "error"]},
        EventType.STATUS_UPDATE.value: {"required": ["cell", "state"], "optional": ["metrics"]},
    }
    
    def validate(self, event_type: str, payload: dict) -> bool:
        schema = self.SCHEMA.get(event_type)
        if not schema:
            return True
        return all(k in payload for k in schema["required"])
    
    def build(self, event_type: EventType, payload: dict) -> dict:
        return {"type": event_type.value, "payload": payload, "version": "12.0"}
