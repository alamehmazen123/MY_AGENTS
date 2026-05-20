import pytest


@pytest.mark.asyncio
async def test_system_lifecycle():
    from kernel.main import LifespanManager
    lm = LifespanManager()
    await lm.start()
    assert lm.running
    await lm.shutdown()
    assert not lm.running
