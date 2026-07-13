"""Determinism: identical inputs must give byte-identical outputs."""

from __future__ import annotations

from .conftest import make_cointegrated_pair, run


def test_same_input_twice_gives_identical_output(actionable_pair):
    first = run(*actionable_pair)
    second = run(*actionable_pair)
    assert first.model_dump() == second.model_dump()


def test_regenerated_fixture_gives_identical_output():
    """The seeded generator itself is deterministic end to end."""
    first = run(*make_cointegrated_pair())
    second = run(*make_cointegrated_pair())
    assert first.model_dump() == second.model_dump()
