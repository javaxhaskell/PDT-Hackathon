"""Backtest mechanics: next-open execution, exits, costs and the screen gate.

The unit tests drive app.quant.backtest.run_backtest directly with
hand-crafted z-score paths and flat prices, so each rule can be checked
in isolation and deterministically.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app import config
from app.quant import backtest as bt
from app.schemas import ExitReason, FinalState

from .conftest import run


def _flat_inputs(n: int = 60, price_a: float = 100.0, price_b: float = 50.0):
    dates = pd.bdate_range("2021-01-04", periods=n)
    ones = np.ones(n)
    return dates, ones * price_a, ones * price_b, ones * price_a, ones * price_b


def _run(z: np.ndarray, n: int = 60, cost_bps: float = 10.0, eval_start: int = 5):
    dates, open_a, open_b, close_a, close_b = _flat_inputs(n)
    return bt.run_backtest(
        dates=dates,
        open_a=open_a,
        open_b=open_b,
        close_a=close_a,
        close_b=close_b,
        z=z,
        eval_start=eval_start,
        beta=1.0,
        cost_bps=cost_bps,
    )


def test_close_signal_executes_at_next_open():
    z = np.full(60, 1.0)
    z[20] = 2.5   # entry signal at the close of index 20
    z[23] = 0.3   # exit signal at the close of index 23
    trades, _ = _run(z)
    assert len(trades) == 1
    trade = trades[0]
    dates = pd.bdate_range("2021-01-04", periods=60)
    assert trade.signal_date == dates[20].strftime("%Y-%m-%d")
    assert trade.entry_date == dates[21].strftime("%Y-%m-%d")   # next open
    assert trade.exit_signal_date == dates[23].strftime("%Y-%m-%d")
    assert trade.exit_date == dates[24].strftime("%Y-%m-%d")    # next open again
    assert trade.exit_reason == ExitReason.TARGET
    assert trade.holding_days == 3
    # Positive z means canonical A is rich: sell A, buy B.
    assert trade.direction == "SELL_A_BUY_B"
    assert trade.qty_a < 0 and trade.qty_b > 0


def test_stop_rule_exits_next_open():
    z = np.full(60, 1.5)
    z[20] = 2.5   # entry
    z[25] = 3.6   # beyond the 3.5 stop
    trades, _ = _run(z)
    assert len(trades) == 1
    assert trades[0].exit_reason == ExitReason.STOP
    assert trades[0].holding_days == 5


def test_max_holding_rule_forces_time_exit():
    z = np.full(60, 1.0)
    z[20] = 2.5
    z[21:] = 1.0  # never reaches target (0.5) or stop (3.5)
    trades, _ = _run(z)
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_reason == ExitReason.TIME
    # The time stop fires at the close of the MAX_HOLDING_DAYS-th day after
    # entry and executes at the next open, so one extra day is recorded.
    assert trade.holding_days == config.MAX_HOLDING_DAYS + 1


def test_open_position_closes_at_final_close():
    n = 60
    z = np.full(n, 1.0)
    z[n - 3] = -2.5  # entry signal two days before the end
    trades, _ = _run(z, n=n)
    assert len(trades) == 1
    trade = trades[0]
    assert trade.direction == "BUY_A_SELL_B"
    assert trade.exit_reason == ExitReason.END_OF_SAMPLE
    assert trade.exit_signal_date is None
    dates = pd.bdate_range("2021-01-04", periods=n)
    assert trade.entry_date == dates[n - 2].strftime("%Y-%m-%d")
    assert trade.exit_date == dates[n - 1].strftime("%Y-%m-%d")
    # Executed at the final CLOSE because no next open exists.
    assert trade.exit_price_a == pytest.approx(100.0)


def test_entry_signal_on_last_day_is_dropped():
    z = np.full(60, 1.0)
    z[-1] = 2.5  # nothing can execute after this close
    trades, _ = _run(z)
    assert trades == []


def test_costs_hit_both_legs_at_entry_and_exit():
    """Flat prices isolate costs: pnl must be exactly the four cost events."""
    z = np.full(60, 1.0)
    z[20] = 2.5
    z[23] = 0.3
    cost_bps = 10.0
    trades, _ = _run(z, cost_bps=cost_bps)
    trade = trades[0]
    cost_rate = cost_bps * 1e-4
    # Entry: both legs together are exactly 1 unit of gross notional; with
    # flat prices the exit notional is 1 unit again.
    assert trade.costs == pytest.approx(2.0 * cost_rate)
    assert trade.pnl == pytest.approx(-2.0 * cost_rate)


def test_only_one_position_at_a_time():
    z = np.full(60, 2.5)  # permanently stretched
    trades, _ = _run(z)
    # z stays between exit and stop forever, so every trade runs into the
    # time limit and re-enters; positions must never overlap.
    assert len(trades) >= 2
    for earlier, later in zip(trades, trades[1:], strict=False):
        assert earlier.exit_date <= later.entry_date


def test_equity_curve_starts_flat_and_compounds():
    z = np.full(60, 1.0)
    z[20] = 2.5
    z[23] = 0.3
    trades, equity = _run(z)
    assert equity[0].value == pytest.approx(1.0)  # flat before the first entry
    expected_final = float(np.prod([1.0 + t.pnl for t in trades]))
    assert equity[-1].value == pytest.approx(expected_final)


def test_metrics_gate_and_limited_evidence(good_pair):
    result = run(*good_pair)
    metrics = result.backtest
    assert metrics.screen_passed
    assert metrics.n_trades == len(result.trades)
    assert metrics.total_costs > 0
    assert metrics.gross_return > metrics.net_return  # costs always drag
    if config.MIN_TRADES <= metrics.n_trades < config.LIMITED_EVIDENCE_TRADES:
        assert metrics.limited_evidence


def test_engine_trades_execute_at_recorded_next_open(good_pair):
    """End-to-end: ledger prices equal the actual next-day opens."""
    df_a, df_b = good_pair
    result = run(df_a, df_b)
    date_strings = [d.strftime("%Y-%m-%d") for d in df_a.index]
    for trade in result.trades:
        signal_idx = date_strings.index(trade.signal_date)
        assert trade.entry_date == date_strings[signal_idx + 1]
        assert trade.entry_price_a == pytest.approx(float(df_a["open"].iloc[signal_idx + 1]))
        assert trade.entry_price_b == pytest.approx(float(df_b["open"].iloc[signal_idx + 1]))
        if trade.exit_reason != ExitReason.END_OF_SAMPLE:
            exit_signal_idx = date_strings.index(trade.exit_signal_date)
            assert trade.exit_date == date_strings[exit_signal_idx + 1]
            assert trade.exit_price_a == pytest.approx(
                float(df_a["open"].iloc[exit_signal_idx + 1])
            )


def test_high_costs_turn_marginal_candidate_into_screen_failure(good_pair):
    df_a, df_b = good_pair
    cheap = run(df_a, df_b, cost_bps=10.0)
    dear = run(df_a, df_b, cost_bps=200.0)
    assert cheap.backtest.screen_passed
    assert dear.state == FinalState.HISTORICAL_SCREEN_FAILED
    assert not dear.backtest.screen_passed
    assert dear.backtest.net_profit < cheap.backtest.net_profit
    assert dear.backtest.total_costs > cheap.backtest.total_costs
