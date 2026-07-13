"""Suitability filter tests (spec section 10, first four items)."""

from __future__ import annotations

import json

import numpy as np

from app import config
from app.schemas import CardStatus, FinalState

from .conftest import (
    make_changing_beta_pair,
    make_frames,
    make_independent_pair,
    make_low_correlation_pair,
    run,
)

EXPECTED_CARD_KEYS = [
    "move_together",
    "stable_relationship",
    "unusual_today",
    "worked_historically",
]


def _card(result, key):
    return next(c for c in result.evidence_cards if c.key == key)


def test_related_mean_reverting_pair_passes(good_pair):
    result = run(*good_pair)
    assert result.state not in (
        FinalState.UNSUITABLE_PAIR,
        FinalState.HISTORICAL_SCREEN_FAILED,
    )
    assert result.relationship is not None
    assert result.relationship.correlation >= config.MIN_CORRELATION
    assert result.relationship.beta > 0
    assert result.relationship.split_beta_change <= config.MAX_SPLIT_BETA_CHANGE
    assert result.relationship.mean_crossings >= config.MIN_MEAN_CROSSINGS
    assert result.backtest is not None
    assert result.backtest.screen_passed
    assert result.backtest.n_trades >= config.MIN_TRADES
    assert _card(result, "move_together").status == CardStatus.PASS
    assert _card(result, "stable_relationship").status == CardStatus.PASS


def test_independent_random_series_fail_suitability():
    result = run(*make_independent_pair())
    assert result.state == FinalState.UNSUITABLE_PAIR
    assert result.sizing is None
    assert "correlation" in result.explanation


def test_low_correlation_pair_fails():
    result = run(*make_low_correlation_pair())
    assert result.state == FinalState.UNSUITABLE_PAIR
    assert result.relationship.correlation < config.MIN_CORRELATION
    assert _card(result, "move_together").status == CardStatus.FAIL


def test_changing_beta_pair_fails():
    result = run(*make_changing_beta_pair())
    assert result.state == FinalState.UNSUITABLE_PAIR
    # It fails specifically on the split-formation stability check, not on
    # correlation: the returns still move together strongly.
    assert result.relationship.correlation >= config.MIN_CORRELATION
    assert result.relationship.split_beta_change > config.MAX_SPLIT_BETA_CHANGE
    assert _card(result, "stable_relationship").status == CardStatus.FAIL
    assert "beta changed" in result.explanation


def test_exactly_four_cards_in_checklist_order(good_pair):
    result = run(*good_pair)
    assert [c.key for c in result.evidence_cards] == EXPECTED_CARD_KEYS
    for card in result.evidence_cards:
        assert card.headline_value
        assert card.detail_lines
        assert card.how_this_works
        assert card.plain_english


def test_negative_beta_pair_fails_without_crashing():
    """An inverse pair yields an invalid (negative) beta; the engine must
    degrade gracefully: no signal/backtest/charts, four cards, JSON-safe."""
    rng = np.random.default_rng(5)
    x = np.cumsum(rng.normal(0.0, 0.02, 600))
    log_b = np.log(50.0) + x
    log_a = np.log(80.0) - x + rng.normal(0.0, 0.002, 600)
    df_a, df_b = make_frames(log_a, log_b, seed=5)

    result = run(df_a, df_b)
    assert result.state == FinalState.UNSUITABLE_PAIR
    assert result.relationship.beta < 0
    assert result.signal is None
    assert result.backtest is None
    assert result.charts is None
    assert len(result.evidence_cards) == 4
    assert _card(result, "unusual_today").headline_value == "n/a"
    json.dumps(result.model_dump())  # no NaN or Infinity anywhere


def test_cards_show_values_and_thresholds(good_pair):
    result = run(*good_pair)
    move = _card(result, "move_together")
    assert f"{config.MIN_CORRELATION:.2f}" in " ".join(move.detail_lines)
    worked = _card(result, "worked_historically")
    joined = " ".join(worked.detail_lines)
    assert str(config.MIN_TRADES) in joined
    assert f"{config.MAX_DRAWDOWN_LIMIT:.0%}" in joined
