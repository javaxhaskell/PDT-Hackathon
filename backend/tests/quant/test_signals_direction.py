"""Signal direction, WAIT, canonical ordering and no-lookahead tests."""

from __future__ import annotations

import pytest

from app import config
from app.schemas import CardStatus, FinalState

from .conftest import force_final_z, run


def test_positive_z_gives_sell_a_buy_b(actionable_pair):
    result = run(*actionable_pair)
    assert result.signal.z_score == pytest.approx(2.5, abs=1e-6)
    assert result.state == FinalState.SELL_A_BUY_B
    # Every historical short-A trade must be signed accordingly.
    for trade in result.trades:
        if trade.direction == "SELL_A_BUY_B":
            assert trade.qty_a < 0 and trade.qty_b > 0
        else:
            assert trade.qty_a > 0 and trade.qty_b < 0


def test_negative_z_gives_buy_a_sell_b(good_pair):
    df_a, df_b = force_final_z(*good_pair, target_z=-2.5)
    result = run(df_a, df_b)
    assert result.signal.z_score == pytest.approx(-2.5, abs=1e-6)
    assert result.state == FinalState.BUY_A_SELL_B


def test_small_z_gives_wait(good_pair):
    df_a, df_b = force_final_z(*good_pair, target_z=0.2)
    result = run(df_a, df_b)
    assert result.signal.z_score == pytest.approx(0.2, abs=1e-6)
    assert result.state == FinalState.WAIT
    assert result.sizing is None


def test_caution_band_on_unusual_today_card(good_pair):
    df_a, df_b = force_final_z(*good_pair, target_z=1.7)
    result = run(df_a, df_b)
    card = next(c for c in result.evidence_cards if c.key == "unusual_today")
    assert card.status == CardStatus.CAUTION


def test_swapped_display_order_flips_direction(actionable_pair):
    """The same data entered as (BBB, AAA) must mirror every displayed sign."""
    df_a, df_b = actionable_pair
    canonical = run(df_a, df_b, ticker_a="AAA", ticker_b="BBB")
    swapped = run(df_b, df_a, ticker_a="BBB", ticker_b="AAA")

    # Canonical A is rich: sell AAA / buy BBB. Displayed as (BBB, AAA) that
    # becomes: buy displayed A (BBB), sell displayed B (AAA).
    assert canonical.state == FinalState.SELL_A_BUY_B
    assert swapped.state == FinalState.BUY_A_SELL_B
    assert swapped.signal.z_score == pytest.approx(-canonical.signal.z_score, abs=1e-9)

    # Sizing must agree per ticker, not per slot.
    legs_c = {leg.ticker: leg for leg in canonical.sizing.legs}
    legs_s = {leg.ticker: leg for leg in swapped.sizing.legs}
    assert legs_c.keys() == legs_s.keys() == {"AAA", "BBB"}
    for ticker in ("AAA", "BBB"):
        assert legs_c[ticker].side == legs_s[ticker].side
        assert legs_c[ticker].shares == legs_s[ticker].shares
    assert legs_c["AAA"].side == "SELL"
    assert legs_c["BBB"].side == "BUY"
    # The displayed ticker A's leg comes first in each view.
    assert canonical.sizing.legs[0].ticker == "AAA"
    assert swapped.sizing.legs[0].ticker == "BBB"

    # Displayed trade signs always match the displayed direction label.
    for trade in swapped.trades:
        if trade.direction == "BUY_A_SELL_B":
            assert trade.qty_a > 0 and trade.qty_b < 0
        else:
            assert trade.qty_a < 0 and trade.qty_b > 0


def test_canonical_ordering_is_deterministic(actionable_pair):
    """(AAA, BBB) and (BBB, AAA) are the same analysis under the hood."""
    df_a, df_b = actionable_pair
    canonical = run(df_a, df_b, ticker_a="AAA", ticker_b="BBB")
    swapped = run(df_b, df_a, ticker_a="BBB", ticker_b="AAA")

    assert canonical.backtest.model_dump() == swapped.backtest.model_dump()
    assert canonical.relationship.correlation == swapped.relationship.correlation
    assert canonical.relationship.mean_crossings == swapped.relationship.mean_crossings
    # Displayed beta is re-expressed for the displayed regression direction.
    assert swapped.relationship.beta == pytest.approx(1.0 / canonical.relationship.beta)
    assert swapped.relationship.leg_weight_a == pytest.approx(
        canonical.relationship.leg_weight_b
    )
    # The after-cost equity curve does not depend on display order.
    assert canonical.charts.equity.model_dump() == swapped.charts.equity.model_dump()


def test_no_rolling_value_uses_future_rows(good_pair):
    """Perturbing future prices must not change any earlier displayed value."""
    df_a, df_b = good_pair
    n = len(df_a)
    k = n - 40  # deep inside the evaluation period, far past the formation end
    df_a2 = df_a.copy()
    df_a2.iloc[k:, :] = df_a2.iloc[k:, :] * 1.05  # bump open AND close from k onward

    base = run(df_a, df_b)
    bumped = run(df_a2, df_b)
    cutoff = df_a.index[k].strftime("%Y-%m-%d")

    spread_base = {p.date: p.value for p in base.charts.spread.spread}
    spread_bump = {p.date: p.value for p in bumped.charts.spread.spread}
    assert {d: v for d, v in spread_base.items() if d < cutoff} == {
        d: v for d, v in spread_bump.items() if d < cutoff
    }
    mean_base = {p.date: p.value for p in base.charts.spread.rolling_mean}
    mean_bump = {p.date: p.value for p in bumped.charts.spread.rolling_mean}
    assert {d: v for d, v in mean_base.items() if d < cutoff} == {
        d: v for d, v in mean_bump.items() if d < cutoff
    }
    # Trades fully completed before the perturbation are byte-identical.
    done_base = [t for t in base.trades if t.exit_date and t.exit_date < cutoff]
    done_bump = [t for t in bumped.trades if t.exit_date and t.exit_date < cutoff]
    assert [t.model_dump() for t in done_base] == [t.model_dump() for t in done_bump]


def test_formation_parameters_stay_frozen(good_pair):
    """Evaluation-period data must never leak into the fitted relationship."""
    df_a, df_b = good_pair
    n = len(df_a)
    split = int(n * config.FORMATION_FRACTION)
    df_a2 = df_a.copy()
    df_a2.iloc[split + 5 :, :] = df_a2.iloc[split + 5 :, :] * 1.10

    base = run(df_a, df_b)
    bumped = run(df_a2, df_b)
    assert base.relationship.beta == bumped.relationship.beta
    assert base.relationship.intercept == bumped.relationship.intercept
    assert base.relationship.split_beta_change == bumped.relationship.split_beta_change
    assert base.relationship.formation_end == df_a.index[split - 1].strftime("%Y-%m-%d")
    assert base.relationship.evaluation_start == df_a.index[split].strftime("%Y-%m-%d")
    assert base.charts.spread.formation_end == base.relationship.formation_end
