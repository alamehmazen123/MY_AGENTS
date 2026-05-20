import pytest
from cells.runtime.queue import SprintQueue
from cells.runtime.model_manager import ModelManager, ModelState
from cells.runtime.circuit_breaker import CircuitBreaker
from cells.runtime.stream_buffer import StreamBuffer


@pytest.mark.asyncio
async def test_queue_priority():
    q = SprintQueue()
    id1 = await q.enqueue({"prompt": "a", "priority": 1})
    id2 = await q.enqueue({"prompt": "b", "priority": 5})
    first = q.pop()
    assert first["priority"] == 5


@pytest.mark.asyncio
async def test_model_manager():
    m = ModelManager()
    assert await m.load("model_a")
    assert m.get_active() == "model_a"
    assert await m.switch("model_a", "model_b")
    assert m.get_active() == "model_b"


def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
    assert not cb.is_open("m")
    cb.record_failure("m")
    cb.record_failure("m")
    assert cb.is_open("m")
    import time
    time.sleep(0.02)
    assert not cb.is_open("m")


def test_stream_buffer_backpressure():
    b = StreamBuffer(max_size=2)
    b.start()
    assert b.push("a")
    assert b.push("b")
    assert not b.push("c")  # Backpressure
    b.end()
