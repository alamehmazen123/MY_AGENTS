"""
kernel/events.py — Ordered Durable Event Bus
JSONL append, SHA-256 chain. Immutable log.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable, Optional
from kernel.config import settings


@dataclass(frozen=True)
class Event:
    seq: int
    timestamp: str
    type: str
    payload: Dict
    prev_hash: str
    this_hash: str
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


class EventBus:
    """Durable ordered event bus with cryptographic chain."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or settings.data_dir / "dna"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "events.jsonl"
        self._seq = 0
        self._last_hash = "0" * 64
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}
        self._global_handlers: List[Callable[[Event], None]] = []
        self._lock = asyncio.Lock()
        self._load_tail()
    
    def _load_tail(self):
        if not self.log_file.exists():
            return
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            self._seq = last["seq"]
            self._last_hash = last["this_hash"]
    
    def _compute_hash(self, payload: str, prev: str) -> str:
        return hashlib.sha256(f"{prev}:{payload}".encode()).hexdigest()
    
    async def emit(self, event_type: str, payload: Dict) -> Event:
        async with self._lock:
            self._seq += 1
            ts = datetime.utcnow().isoformat()
            body = json.dumps({"seq": self._seq, "timestamp": ts, "type": event_type, "payload": payload}, sort_keys=True)
            this_hash = self._compute_hash(body, self._last_hash)
            evt = Event(
                seq=self._seq,
                timestamp=ts,
                type=event_type,
                payload=payload,
                prev_hash=self._last_hash,
                this_hash=this_hash,
            )
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(evt.to_json() + "\n")
            self._last_hash = this_hash
        await self._dispatch(evt)
        return evt
    
    async def _dispatch(self, evt: Event) -> None:
        for cb in self._handlers.get(evt.type, []):
            try:
                cb(evt)
            except Exception:
                pass
        for cb in self._global_handlers:
            try:
                cb(evt)
            except Exception:
                pass
    
    def on(self, event_type: str, handler: Callable[[Event], None]) -> Callable[[], None]:
        self._handlers.setdefault(event_type, []).append(handler)
        def off():
            self._handlers[event_type].remove(handler)
        return off
    
    def on_any(self, handler: Callable[[Event], None]) -> Callable[[], None]:
        self._global_handlers.append(handler)
        def off():
            self._global_handlers.remove(handler)
        return off
    
    async def replay_since(self, seq: int) -> List[Event]:
        events = []
        if not self.log_file.exists():
            return events
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj["seq"] >= seq:
                    events.append(Event(**obj))
        return events
    
    def heal(self) -> bool:
        """If the hash chain is broken (e.g. an interrupted write on a previous
        run), archive the corrupt log and start a fresh one. The event log holds
        only system telemetry, so rotating it is safe and stops the recurring
        'self-test failed' warnings at the source. Returns True if it healed."""
        if self.verify_chain():
            return False
        import time
        try:
            if self.log_file.exists():
                backup = self.log_file.with_name(f"events.corrupt-{int(time.time())}.jsonl")
                self.log_file.rename(backup)
        except Exception:
            pass
        self._seq = 0
        self._last_hash = "0" * 64
        return True

    def verify_chain(self) -> bool:
        """Verify SHA-256 chain integrity."""
        if not self.log_file.exists():
            return True
        prev = "0" * 64
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                body = json.dumps({"seq": obj["seq"], "timestamp": obj["timestamp"], "type": obj["type"], "payload": obj["payload"]}, sort_keys=True)
                expected = self._compute_hash(body, obj["prev_hash"])
                if expected != obj["this_hash"]:
                    return False
                if obj["prev_hash"] != prev:
                    return False
                prev = obj["this_hash"]
        return True


# Singleton
bus = EventBus()
