"""Step 4 of the PairScope model: did the unchanged rule work historically?

A strictly chronological simulation over the held-out evaluation period
(the final 40% of dates, which the fit never saw):

- The decision is made from each day's CLOSE (that day's z-score).
- Execution happens at the NEXT trading day's OPEN — you cannot trade on
  a price you have only just observed.
- At most one pair position is open at any time.
- Trading costs are charged on BOTH legs at entry and again on BOTH legs
  at exit (four cost events per round trip).
- Short-sale proceeds are collateral, never reusable cash.

Everything works in CANONICAL ticker order; direction labels here mean
canonical A/B. The engine maps them to the user's displayed order.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app import config
from app.schemas import BacktestMetrics, ExitReason, SeriesPoint, TradeRecord

# Basis points to fraction (1 bp = 0.01% = 1e-4). A unit conversion, not a threshold.
BPS = 1e-4


@dataclass
class _OpenPosition:
    """A live pair position with quantities frozen at the entry open."""

    direction: str        # canonical "SELL_A_BUY_B" or "BUY_A_SELL_B"
    signal_idx: int       # the close whose z-score triggered entry
    entry_idx: int        # executed at this day's open
    qty_a: float          # signed units per 1 unit of gross exposure
    qty_b: float
    entry_price_a: float
    entry_price_b: float
    entry_cost: float     # both entry legs, fraction of gross exposure
    equity_base: float    # equity just before this trade


def run_backtest(
    *,
    dates: pd.DatetimeIndex,
    open_a: np.ndarray,
    open_b: np.ndarray,
    close_a: np.ndarray,
    close_b: np.ndarray,
    z: np.ndarray,
    eval_start: int,
    beta: float,
    cost_bps: float,
) -> tuple[list[TradeRecord], list[SeriesPoint]]:
    """Simulate the fixed z-score rule over evaluation dates only.

    Returns the completed-trade ledger and the daily after-cost equity
    curve (starting at 1.0, flat while no position is open, marked to
    market at adjusted closes while a position is open).
    """
    cost_rate = cost_bps * BPS
    # One unit of gross exposure split by the frozen hedge ratio:
    # A carries 1/(1+beta) of the money, B carries beta/(1+beta).
    w_a = 1.0 / (1.0 + beta)
    w_b = beta / (1.0 + beta)

    trades: list[TradeRecord] = []
    equity_points: list[SeriesPoint] = []
    equity = 1.0
    pos: _OpenPosition | None = None
    pending_entry: str | None = None
    pending_entry_signal_idx: int = -1
    pending_exit: ExitReason | None = None
    pending_exit_signal_idx: int | None = None
    last = len(dates) - 1

    def _date(i: int) -> str:
        return dates[i].strftime("%Y-%m-%d")

    def _close_trade(
        position: _OpenPosition,
        exit_idx: int,
        px_a: float,
        px_b: float,
        reason: ExitReason,
        exit_signal_idx: int | None,
    ) -> tuple[TradeRecord, float]:
        """Realise a trade at the given exit prices and return (record, new equity)."""
        gross_pnl = position.qty_a * (px_a - position.entry_price_a) + position.qty_b * (
            px_b - position.entry_price_b
        )
        # Exit costs are charged on the notional actually traded at exit prices.
        exit_cost = cost_rate * (abs(position.qty_a) * px_a + abs(position.qty_b) * px_b)
        pnl = gross_pnl - position.entry_cost - exit_cost
        record = TradeRecord(
            signal_date=_date(position.signal_idx),
            entry_date=_date(position.entry_idx),
            exit_signal_date=_date(exit_signal_idx) if exit_signal_idx is not None else None,
            exit_date=_date(exit_idx),
            direction=position.direction,  # type: ignore[arg-type]
            entry_beta=beta,
            qty_a=position.qty_a,
            qty_b=position.qty_b,
            entry_price_a=position.entry_price_a,
            entry_price_b=position.entry_price_b,
            exit_price_a=px_a,
            exit_price_b=px_b,
            costs=position.entry_cost + exit_cost,
            exit_reason=reason,
            holding_days=exit_idx - position.entry_idx,
            pnl=pnl,
        )
        return record, position.equity_base * (1.0 + pnl)

    for i in range(eval_start, last + 1):
        # ------ 1) executions at today's OPEN (decided at yesterday's close) ------
        if pos is not None and pending_exit is not None:
            record, equity = _close_trade(
                pos, i, float(open_a[i]), float(open_b[i]), pending_exit, pending_exit_signal_idx
            )
            trades.append(record)
            pos = None
            pending_exit = None
            pending_exit_signal_idx = None
        if pos is None and pending_entry is not None:
            oa, ob = float(open_a[i]), float(open_b[i])
            if pending_entry == "SELL_A_BUY_B":
                qty_a = -w_a / oa  # short the expensive leg
                qty_b = +w_b / ob  # long the cheap leg
            else:
                qty_a = +w_a / oa
                qty_b = -w_b / ob
            entry_cost = cost_rate * (abs(qty_a) * oa + abs(qty_b) * ob)
            pos = _OpenPosition(
                direction=pending_entry,
                signal_idx=pending_entry_signal_idx,
                entry_idx=i,
                qty_a=qty_a,
                qty_b=qty_b,
                entry_price_a=oa,
                entry_price_b=ob,
                entry_cost=entry_cost,
                equity_base=equity,
            )
            pending_entry = None

        # ------ 2) decision from today's CLOSE (today's z-score) ------
        zi = float(z[i]) if np.isfinite(z[i]) else float("nan")
        if pos is not None:
            held = i - pos.entry_idx
            # Exit precedence when several rules fire on the same close:
            # target first, then stop, then the time limit (documented in MODEL.md).
            if np.isfinite(zi) and abs(zi) <= config.EXIT_Z:
                pending_exit = ExitReason.TARGET
                pending_exit_signal_idx = i
            elif np.isfinite(zi) and abs(zi) >= config.STOP_Z:
                pending_exit = ExitReason.STOP
                pending_exit_signal_idx = i
            elif held >= config.MAX_HOLDING_DAYS:
                pending_exit = ExitReason.TIME
                pending_exit_signal_idx = i
        else:
            # An entry signal on the very last date is dropped: there is no
            # next open to execute at (documented in MODEL.md).
            if np.isfinite(zi) and abs(zi) >= config.ENTRY_Z and i < last:
                # Positive z: A is rich relative to B -> sell A, buy B.
                pending_entry = "SELL_A_BUY_B" if zi > 0 else "BUY_A_SELL_B"
                pending_entry_signal_idx = i

        # ------ 3) end of sample: force-close at the FINAL CLOSE ------
        # No next open exists, so the last close is the only executable price.
        if i == last and pos is not None:
            record, equity = _close_trade(
                pos, i, float(close_a[i]), float(close_b[i]), ExitReason.END_OF_SAMPLE, None
            )
            trades.append(record)
            pos = None
            pending_exit = None
            pending_exit_signal_idx = None

        # ------ 4) mark equity at today's close ------
        if pos is not None:
            mtm = (
                pos.qty_a * (float(close_a[i]) - pos.entry_price_a)
                + pos.qty_b * (float(close_b[i]) - pos.entry_price_b)
                - pos.entry_cost
            )
            eq_value = pos.equity_base * (1.0 + mtm)
        else:
            eq_value = equity
        equity_points.append(SeriesPoint(date=_date(i), value=round(float(eq_value), 8)))

    return trades, equity_points


def max_drawdown(equity_points: list[SeriesPoint]) -> float:
    """Worst peak-to-trough fall of the daily equity curve (a negative number)."""
    worst = 0.0
    peak = float("-inf")
    for point in equity_points:
        value = point.value if point.value is not None else 0.0
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst


def compute_metrics(
    trades: list[TradeRecord], equity_points: list[SeriesPoint]
) -> BacktestMetrics:
    """Summarise the trade ledger and equity curve, then apply the screen gate.

    The gate is a product decision, not proof of future profit: at least
    MIN_TRADES completed trades, positive net profit after costs, profit
    factor above MIN_PROFIT_FACTOR and a drawdown no worse than
    MAX_DRAWDOWN_LIMIT.
    """
    n = len(trades)
    pnls = [t.pnl for t in trades if t.pnl is not None]
    costs_total = float(sum(t.costs for t in trades))
    gross_pnls = [p + t.costs for p, t in zip(pnls, trades, strict=True)]

    net_profit = float(sum(pnls))
    net_return = float(np.prod([1.0 + p for p in pnls]) - 1.0) if pnls else 0.0
    gross_return = float(np.prod([1.0 + p for p in gross_pnls]) - 1.0) if gross_pnls else 0.0

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate = len(wins) / n if n else None
    avg_win = float(np.mean(wins)) if wins else None
    avg_loss = float(np.mean(losses)) if losses else None
    # Profit factor = gross wins / |gross losses|. Undefined (None) when
    # there are no losing trades; the gate treats that as a pass provided
    # there is at least one winning trade.
    profit_factor = float(sum(wins) / abs(sum(losses))) if losses else None

    mdd = max_drawdown(equity_points)
    avg_holding = (
        float(np.mean([t.holding_days for t in trades if t.holding_days is not None]))
        if n
        else None
    )
    worst_trade = float(min(pnls)) if pnls else None

    profit_factor_ok = (
        profit_factor > config.MIN_PROFIT_FACTOR
        if profit_factor is not None
        else len(wins) > 0
    )
    screen_passed = bool(
        n >= config.MIN_TRADES
        and net_profit > 0.0
        and profit_factor_ok
        and mdd >= config.MAX_DRAWDOWN_LIMIT
    )
    limited_evidence = bool(config.MIN_TRADES <= n < config.LIMITED_EVIDENCE_TRADES)

    return BacktestMetrics(
        n_trades=n,
        net_profit=net_profit,
        net_return=net_return,
        gross_return=gross_return,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        max_drawdown=mdd,
        avg_holding_days=avg_holding,
        total_costs=costs_total,
        screen_passed=screen_passed,
        limited_evidence=limited_evidence,
        worst_trade_pnl=worst_trade,
    )
