"""tests/mcp/test_runtime.py — MCP runtime and process isolation tests."""
import pytest
import asyncio
from kernel.mcp.runtime.process_executor import ProcessExecutor
from kernel.mcp.protocol.adapter import InternalToolAdapter
from kernel.security.execution_policy import ExecutionPolicy
from kernel.security.resource_limits import ResourceLimits


def dummy_handler(args):
    return {"echo": args.get("msg", "")}


def crash_handler(args):
    raise RuntimeError("intentional_crash")



@pytest.mark.asyncio
async def test_process_executor_ok():
    tool = InternalToolAdapter.adapt(
        "dummy", "test", dummy_handler, set(), ExecutionPolicy(), timeout=5.0
    )
    exe = ProcessExecutor()
    result = await exe.run(tool, {"msg": "hello"})
    assert result.get("status") == "ok"
    assert result["echo"] == "hello"


@pytest.mark.asyncio
async def test_process_executor_crash_containment():
    tool = InternalToolAdapter.adapt(
        "crash", "test", crash_handler, set(), ExecutionPolicy(), timeout=5.0
    )
    exe = ProcessExecutor()
    result = await exe.run(tool, {})
    assert result.get("status") == "error"
    assert "intentional_crash" in result.get("error", "")


@pytest.mark.asyncio
async def test_process_executor_timeout():
    # Use _test_sleep preset to test worker timeout enforcement
    tool = InternalToolAdapter.adapt(
        "_test_sleep", "test", None, set(), ExecutionPolicy(), timeout=2.0
    )
    exe = ProcessExecutor()
    result = await exe.run(tool, {"duration": 30})
    assert result.get("status") == "killed"
    assert result.get("error") == "execution_timeout"


@pytest.mark.asyncio
async def test_resource_limits_applied():
    limits = ResourceLimits(memory_mb=64, cpu_seconds=1, timeout=2)
    tool = InternalToolAdapter.adapt(
        "dummy2", "test", dummy_handler, set(),
        ExecutionPolicy(limits=limits), timeout=2.0
    )
    exe = ProcessExecutor()
    result = await exe.run(tool, {"msg": "ok"})
    assert result.get("status") == "ok"
