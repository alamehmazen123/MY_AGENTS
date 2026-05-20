"""
plasma/event_log.py — Immutable JSONL, SHA-256 Chain
Wrapper around kernel.events for persistence queries.
"""
from kernel.events import bus, Event
from typing import List


class EventLog:
    """Query interface for immutable event log."""
    
    async def query(self, event_type: str, limit: int = 100) -> List[Event]:
        # In production, use indexed queries
        # For now, scan recent
        events = await bus.replay_since(max(0, bus._seq - limit))
        return [e for e in events if e.type == event_type]
    
    def verify(self) -> bool:
        return bus.verify_chain()


log = EventLog()
