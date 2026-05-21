import pytest
from unittest.mock import AsyncMock, patch
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

    # Mock Ollama HTTP responses so the test works offline
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"response": "ok", "done": True})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

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
