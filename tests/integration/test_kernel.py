import pytest
from kernel.lattice_verifier import verifier
from kernel.resolution_table import table


def test_lattice_no_cycles():
    assert verifier.verify()


def test_resolution_table_loaded():
    assert table.size > 0


def test_resolution_lookup():
    result = table.lookup(["single_runtime"], "NORMAL", "REASONING")
    assert result["status"] == "SATISFIED"
