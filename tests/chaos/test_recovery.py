import pytest
from kernel.recovery_invariant import RECOVERY_SPEC


def test_recovery_spec_concrete():
    assert RECOVERY_SPEC["max_recovery_time_ms"] <= 5000
    assert RECOVERY_SPEC["max_data_loss_events"] == 0
    assert RECOVERY_SPEC["max_state_rollback_seconds"] <= 30
    assert RECOVERY_SPEC["recovery_verification"] == "automatic"
