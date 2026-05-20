import pytest
from cells.reflex.cell import ReflexCell
from cells.reflex.router import ReflexRouter
from cells.reflex.hydration import HydrationCache
from cells.reflex.safety import SafetyChecker


@pytest.mark.asyncio
async def test_reflex_latency():
    cell = ReflexCell()
    await cell.init()
    import time
    start = time.monotonic()
    result = await cell.handle("health.check", {})
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed < 50
    assert result["status"] == "ok"


def test_router_table():
    r = ReflexRouter()
    assert r.route("health.check", {})["status"] == "ok"
    assert "error" in r.route("unknown", {})


def test_hydration_ttl():
    h = HydrationCache(default_ttl_seconds=0.01)
    h.preload("k", "v")
    assert h.get("k") == "v"
    import time
    time.sleep(0.02)
    assert h.get("k") is None


def test_safety_check():
    s = SafetyChecker()
    assert s.check({"reflex_deterministic", "single_runtime"})
    assert not s.check({"single_runtime"})
