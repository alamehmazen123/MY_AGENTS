import pytest
from cells.deliberation.capsule import Capsule
from cells.deliberation.token_budget import TokenBudget
from cells.deliberation.reasoning_compiler import ReasoningCompiler


def test_capsule_bounds():
    c = Capsule(max_runtime=1.0, max_tokens=10, max_iterations=2)
    c.begin("p", "m")
    assert c.check()
    c.consume(5)
    assert c.remaining_tokens == 5
    c.consume(5)
    assert not c.check()
    c.end()


def test_token_budget():
    b = TokenBudget(100)
    assert b.allocate(50)
    assert not b.allocate(60)
    b.consume(30)
    assert b.remaining == 50


def test_reasoning_compiler():
    rc = ReasoningCompiler()
    assert rc.detect("I will plan the approach") == "planning"
    assert rc.detect("```python\ndef foo():\n```") == "coding"
