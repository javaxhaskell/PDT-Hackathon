"""Position sizing: capital and risk limits, hedge ratio, infeasible cases."""

from __future__ import annotations

import pytest

from app import config
from app.schemas import FinalState

from .conftest import run

_EPS = 1e-6


@pytest.mark.parametrize("profile", ["conservative", "balanced", "aggressive"])
def test_whole_share_sizing_stays_inside_capital_and_risk(actionable_pair, profile):
    capital = 10_000.0
    result = run(*actionable_pair, risk_profile=profile, whole_shares=True)
    sizing = result.sizing
    assert sizing is not None and sizing.sized

    limits = config.RISK_PROFILES[profile]
    assert sizing.gross_exposure <= capital * limits["max_gross_fraction"] * (1 + _EPS)
    assert sizing.stress_loss_estimate <= capital * limits["max_stress_fraction"] * (1 + _EPS)
    assert sizing.risk_budget == pytest.approx(capital * limits["max_stress_fraction"])
    assert sizing.max_gross_allowed == pytest.approx(capital * limits["max_gross_fraction"])
    assert sizing.remaining_cash == pytest.approx(capital - sizing.gross_exposure)
    # Estimated cost covers all four legs: entry now plus exit estimated
    # at current prices (2 x cost_bps x gross).
    assert sizing.estimated_cost == pytest.approx(2.0 * 10.0 * 1e-4 * sizing.gross_exposure)

    assert len(sizing.legs) == 2
    for leg in sizing.legs:
        assert leg.shares >= 1
        assert leg.shares == int(leg.shares)  # whole shares only
        assert leg.notional == pytest.approx(leg.shares * leg.price)
    buy = sum(leg.notional for leg in sizing.legs if leg.side == "BUY")
    sell = sum(leg.notional for leg in sizing.legs if leg.side == "SELL")
    assert sizing.gross_exposure == pytest.approx(buy + sell)
    assert sizing.net_exposure == pytest.approx(buy - sell)


def test_fractional_sizing_preserves_hedge_ratio(actionable_pair):
    result = run(*actionable_pair, whole_shares=False)
    sizing = result.sizing
    assert sizing is not None and sizing.sized
    relationship = result.relationship
    leg_a = next(leg for leg in sizing.legs if leg.ticker == "AAA")
    leg_b = next(leg for leg in sizing.legs if leg.ticker == "BBB")
    target_ratio = relationship.leg_weight_a / relationship.leg_weight_b
    assert leg_a.notional / leg_b.notional == pytest.approx(target_ratio, rel=1e-3)
    # Fractional shares are rounded to the configured number of decimals.
    scale = 10 ** config.FRACTIONAL_DECIMALS
    for leg in sizing.legs:
        assert leg.shares == pytest.approx(round(leg.shares * scale) / scale, abs=1e-12)


def test_fractional_sizing_stays_inside_limits(actionable_pair):
    capital = 10_000.0
    result = run(*actionable_pair, whole_shares=False, risk_profile="conservative")
    sizing = result.sizing
    limits = config.RISK_PROFILES["conservative"]
    assert sizing.gross_exposure <= capital * limits["max_gross_fraction"] * (1 + _EPS)
    assert sizing.stress_loss_estimate <= capital * limits["max_stress_fraction"] * (1 + _EPS)


def test_minimum_whole_share_pair_can_be_infeasible(actionable_pair):
    """Tiny capital: even one share of each leg breaks the limits -> no size."""
    result = run(
        *actionable_pair,
        starting_capital=60.0,
        risk_profile="conservative",
        whole_shares=True,
    )
    # The verdict itself is unchanged; only the sizing reports why it failed.
    assert result.state == FinalState.SELL_A_BUY_B
    sizing = result.sizing
    assert sizing is not None
    assert not sizing.sized
    assert sizing.reason
    assert sizing.legs == []
    assert sizing.remaining_cash == pytest.approx(60.0)


def test_wait_and_failed_states_have_no_sizing(good_pair):
    result = run(*good_pair)  # forced nothing: today's z is small -> WAIT
    assert result.state == FinalState.WAIT
    assert result.sizing is None
    dear = run(*good_pair, cost_bps=200.0)  # screen fails
    assert dear.sizing is None


def test_stress_estimate_uses_worst_losing_trade(actionable_pair):
    result = run(*actionable_pair)
    sizing = result.sizing
    metrics = result.backtest
    worst = metrics.worst_trade_pnl
    assert worst is not None and worst < 0
    assert sizing.stress_loss_estimate == pytest.approx(
        abs(worst) * sizing.gross_exposure, rel=1e-9
    )


def test_whole_share_tie_breaks_prefer_larger_gross():
    # 4/2 and 6/3 shares have mathematically identical notional ratios;
    # floating-point noise must not decide the winner — the tie-break
    # prefers the larger gross exposure (use more of the allowed budget).
    from app.quant.sizing import _whole_share_search

    price_a, price_b = 254.93, 341.05
    allowed_gross = 3053.0
    target_a = allowed_gross / (1 + 0.699)
    target_b = allowed_gross - target_a
    pair = _whole_share_search(target_a, target_b, price_a, price_b, allowed_gross)
    assert pair is not None
    qty_a, qty_b = pair
    gross = qty_a * price_a + qty_b * price_b
    # (6, 3) gross ~= 2553 dominates (4, 2) gross ~= 1702 at the same ratio.
    assert (qty_a, qty_b) == (6, 3), f"got {pair} (gross {gross:.2f})"
