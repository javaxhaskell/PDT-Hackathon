"""PairScope quant engine — the single entry point for one pair analysis.

Pipeline (see docs/MODEL.md for the full plain-English write-up):

1. Canonicalise: sort the two tickers alphabetically and fit/simulate in
   that fixed order, so (KO, PEP) and (PEP, KO) are the same analysis.
2. Steps 1-2: formation-period return correlation and the formation-period OLS
   line between log prices, with the stability safeguards.
3. Step 3: frozen-parameter spread over the full sample and the rolling
   previous-60-day z-score. Today's signal is the last evaluation date.
4. Step 4: chronological backtest on the held-out evaluation period with
   next-open execution and costs on all four legs, then the screen gate.
5. Decision order: UNSUITABLE_PAIR -> HISTORICAL_SCREEN_FAILED -> WAIT ->
   direction. Sizing only for actionable direction states.
6. Map EVERYTHING back to the user's displayed A/B order: the displayed
   BUY_A_SELL_B always means "buy displayed ticker A, sell displayed
   ticker B".

The engine is pure and deterministic: same inputs, same outputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app import config
from app.schemas import (
    FinalState,
    QuantResult,
    RelationshipStats,
    SignalStats,
    SizingResult,
    TradeRecord,
)

from . import backtest as bt
from . import cards as cards_mod
from . import charts as charts_mod
from . import relationship as rel
from . import signals as sig
from . import sizing as sizing_mod

__all__ = ["run_analysis", "QuantResult"]


def run_analysis(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    *,
    ticker_a: str,
    ticker_b: str,
    starting_capital: float,
    risk_profile: str,
    whole_shares: bool,
    cost_bps: float,
) -> QuantResult:
    """Analyse one pair. See docs/INTERFACES.md for the contract.

    df_a / df_b are cleaned, date-aligned frames (identical ascending
    DatetimeIndex, adjusted "open"/"close" columns) in the user's
    DISPLAYED order. The result is returned in displayed order too.
    """
    profile_name = str(getattr(risk_profile, "value", risk_profile)).lower()
    if profile_name not in config.RISK_PROFILES:
        raise ValueError(f"Unknown risk profile: {risk_profile!r}")
    if not df_a.index.equals(df_b.index):
        raise ValueError("df_a and df_b must share an identical DatetimeIndex")

    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Canonicalise: fit and simulate with tickers in alphabetical order
    # (case-insensitive), so the analysis is identical whichever way round
    # the user typed the pair.
    # ------------------------------------------------------------------
    swapped = ticker_a.upper() > ticker_b.upper()
    if swapped:
        c_df_a, c_df_b = df_b, df_a
        c_ticker_a, c_ticker_b = ticker_b, ticker_a
    else:
        c_df_a, c_df_b = df_a, df_b
        c_ticker_a, c_ticker_b = ticker_a, ticker_b
    # Sign that converts canonical spread/z values into displayed ones:
    # when the display order is reversed, "A rich" becomes "B rich".
    sign = -1.0 if swapped else 1.0

    dates = pd.DatetimeIndex(c_df_a.index)
    c_close_a = c_df_a["close"].astype(float)
    c_close_b = c_df_b["close"].astype(float)

    # ------------------------------------------------------------------
    # Steps 1-2: correlation and the frozen formation relationship
    # ------------------------------------------------------------------
    fit = rel.fit_relationship(c_close_a, c_close_b)
    eval_start = fit.eval_start_idx
    formation_end_date = dates[eval_start - 1].strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # Steps 3-4: spread, z-scores and the historical simulation. These
    # need a usable (finite, positive) beta; when beta is invalid we skip
    # them and the suitability check reports why.
    # ------------------------------------------------------------------
    spread_series: pd.Series | None = None
    roll_mean: pd.Series | None = None
    roll_std: pd.Series | None = None
    z_series: pd.Series | None = None
    crossings = 0
    trades_canonical: list[TradeRecord] = []
    equity_points: list = []
    metrics = None

    if fit.beta_valid:
        log_a = np.log(c_close_a.to_numpy(dtype=float))
        log_b = np.log(c_close_b.to_numpy(dtype=float))
        spread_values = sig.compute_spread(log_a, log_b, fit.intercept, fit.beta)
        spread_series = pd.Series(spread_values, index=dates)
        roll_mean, roll_std = sig.rolling_mean_std(spread_series)
        z_series = sig.z_scores(spread_series)
        crossings = sig.mean_crossings(spread_series)

        trades_canonical, equity_points = bt.run_backtest(
            dates=dates,
            open_a=c_df_a["open"].to_numpy(dtype=float),
            open_b=c_df_b["open"].to_numpy(dtype=float),
            close_a=c_close_a.to_numpy(dtype=float),
            close_b=c_close_b.to_numpy(dtype=float),
            z=z_series.to_numpy(dtype=float),
            eval_start=eval_start,
            beta=fit.beta,
            cost_bps=cost_bps,
        )
        metrics = bt.compute_metrics(trades_canonical, equity_points)
    else:
        warnings.append(
            "The fitted relationship (beta) is not a positive finite number, so the "
            "spread, z-score and historical simulation were not computed."
        )

    suitability = rel.check_suitability(fit, crossings)

    # ------------------------------------------------------------------
    # Today's signal: the z-score at the last evaluation date
    # ------------------------------------------------------------------
    z_last: float | None = None
    signal_stats: SignalStats | None = None
    if z_series is not None and np.isfinite(z_series.iloc[-1]):
        assert spread_series is not None and roll_mean is not None and roll_std is not None
        z_last = float(z_series.iloc[-1])
        signal_stats = SignalStats(
            current_spread=sign * float(spread_series.iloc[-1]),
            rolling_mean=sign * float(roll_mean.iloc[-1]),
            rolling_std=float(roll_std.iloc[-1]),
            z_score=sign * z_last,
            as_of_date=dates[-1].strftime("%Y-%m-%d"),
            entry_z=config.ENTRY_Z,
            exit_z=config.EXIT_Z,
            stop_z=config.STOP_Z,
            max_holding_days=config.MAX_HOLDING_DAYS,
        )
    elif fit.beta_valid:
        warnings.append(
            "Today's z-score could not be computed (not enough prior spread history), "
            "so the engine defaults to WAIT."
        )

    # ------------------------------------------------------------------
    # Decision order (after data-level states handled upstream):
    # unsuitable -> screen failed -> wait -> direction
    # ------------------------------------------------------------------
    if not suitability.passed:
        canonical_state = FinalState.UNSUITABLE_PAIR
    elif metrics is None or not metrics.screen_passed:
        canonical_state = FinalState.HISTORICAL_SCREEN_FAILED
    elif z_last is None or abs(z_last) < config.ENTRY_Z:
        canonical_state = FinalState.WAIT
    elif z_last > 0:
        # Canonical A is rich: sell canonical A, buy canonical B.
        canonical_state = FinalState.SELL_A_BUY_B
    else:
        canonical_state = FinalState.BUY_A_SELL_B
    state = _map_state(canonical_state, swapped)

    # ------------------------------------------------------------------
    # Displayed-order relationship stats. When the display order is the
    # reverse of the canonical fit, beta and intercept are re-expressed for
    # the displayed regression direction (beta' = 1/beta), which keeps
    # leg_weight_a == 1/(1+beta') true in displayed terms. The split-beta
    # change and crossings are canonical diagnostics (see docs/MODEL.md).
    # ------------------------------------------------------------------
    if swapped and np.isfinite(fit.beta) and abs(fit.beta) > 1e-12:
        beta_disp = 1.0 / fit.beta
        intercept_disp = -fit.intercept / fit.beta
    elif swapped:
        beta_disp, intercept_disp = 0.0, 0.0
        warnings.append("Displayed beta is unavailable because the canonical beta is zero.")
    else:
        beta_disp, intercept_disp = fit.beta, fit.intercept
    leg_weight_a_disp = fit.leg_weight_b if swapped else fit.leg_weight_a
    leg_weight_b_disp = fit.leg_weight_a if swapped else fit.leg_weight_b

    relationship_stats = RelationshipStats(
        correlation=_finite(fit.correlation),
        beta=_finite(beta_disp),
        intercept=_finite(intercept_disp),
        split_beta_change=_finite(fit.split_beta_change, rel.UNDEFINED_RATIO),
        mean_crossings=crossings,
        leg_weight_a=_finite(leg_weight_a_disp),
        leg_weight_b=_finite(leg_weight_b_disp),
        formation_start=dates[0].strftime("%Y-%m-%d"),
        formation_end=formation_end_date,
        evaluation_start=dates[eval_start].strftime("%Y-%m-%d"),
        evaluation_end=dates[-1].strftime("%Y-%m-%d"),
    )

    # ------------------------------------------------------------------
    # Trade ledger mapped to displayed order
    # ------------------------------------------------------------------
    trades_displayed = [_map_trade(t, swapped, beta_disp) for t in trades_canonical]

    # ------------------------------------------------------------------
    # Sizing: only for actionable direction states
    # ------------------------------------------------------------------
    sizing_result: SizingResult | None = None
    if state in (FinalState.BUY_A_SELL_B, FinalState.SELL_A_BUY_B):
        worst_losing = sizing_mod.worst_losing_pnl_from(
            [t.pnl for t in trades_canonical if t.pnl is not None]
        )
        sizing_result, sizing_warnings = sizing_mod.size_position(
            direction=canonical_state.value,
            ticker_a=c_ticker_a,
            ticker_b=c_ticker_b,
            beta=fit.beta,
            price_a=float(c_close_a.iloc[-1]),
            price_b=float(c_close_b.iloc[-1]),
            capital=starting_capital,
            profile_name=profile_name,
            whole_shares=whole_shares,
            cost_bps=cost_bps,
            worst_losing_pnl=worst_losing,
        )
        warnings.extend(sizing_warnings)
        if swapped and sizing_result.legs:
            # Show the displayed ticker A's leg first.
            sizing_result = sizing_result.model_copy(
                update={"legs": list(reversed(sizing_result.legs))}
            )

    # ------------------------------------------------------------------
    # Evidence cards and charts, in displayed order
    # ------------------------------------------------------------------
    evidence_cards = cards_mod.build_cards(
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        correlation=relationship_stats.correlation,
        beta=relationship_stats.beta,
        split_beta_change=relationship_stats.split_beta_change,
        mean_crossings=crossings,
        leg_weight_a=relationship_stats.leg_weight_a,
        leg_weight_b=relationship_stats.leg_weight_b,
        suitability=suitability,
        signal=signal_stats,
        metrics=metrics,
    )

    charts = None
    if fit.beta_valid:
        assert (
            spread_series is not None
            and roll_mean is not None
            and roll_std is not None
            and z_series is not None
        )
        charts = charts_mod.build_charts(
            dates=dates,
            close_a=df_a["close"].to_numpy(dtype=float),
            close_b=df_b["close"].to_numpy(dtype=float),
            spread=sign * spread_series.to_numpy(dtype=float),
            rolling_mean=sign * roll_mean.to_numpy(dtype=float),
            rolling_std=roll_std.to_numpy(dtype=float),
            z=sign * z_series.to_numpy(dtype=float),
            trades=trades_displayed,
            formation_end=formation_end_date,
            equity_points=equity_points,
        )

    if metrics is not None and metrics.screen_passed and metrics.limited_evidence:
        warnings.append(
            f"The historical screen passed with limited evidence ({metrics.n_trades} "
            "completed trades); treat the result with extra caution."
        )
    if metrics is not None and metrics.profit_factor is None and metrics.n_trades > 0:
        warnings.append(
            "No losing trades in the evaluation period, so the profit factor is undefined."
        )

    explanation = _build_explanation(
        state=state,
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        suitability=suitability,
        metrics=metrics,
        signal=signal_stats,
    )

    return QuantResult(
        state=state,
        explanation=explanation,
        relationship=relationship_stats,
        signal=signal_stats,
        backtest=metrics,
        trades=trades_displayed,
        sizing=sizing_result,
        evidence_cards=evidence_cards,
        charts=charts,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Display-order mapping helpers
# ---------------------------------------------------------------------------


def _map_state(canonical_state: FinalState, swapped: bool) -> FinalState:
    """Direction states are relative to A/B, so a reversed display flips them."""
    if not swapped:
        return canonical_state
    if canonical_state == FinalState.SELL_A_BUY_B:
        return FinalState.BUY_A_SELL_B
    if canonical_state == FinalState.BUY_A_SELL_B:
        return FinalState.SELL_A_BUY_B
    return canonical_state


def _map_trade(trade: TradeRecord, swapped: bool, beta_disp: float) -> TradeRecord:
    """Swap the A/B legs of a canonical trade for a reversed display order."""
    if not swapped:
        return trade
    return TradeRecord(
        signal_date=trade.signal_date,
        entry_date=trade.entry_date,
        exit_signal_date=trade.exit_signal_date,
        exit_date=trade.exit_date,
        direction=(
            "BUY_A_SELL_B" if trade.direction == "SELL_A_BUY_B" else "SELL_A_BUY_B"
        ),
        entry_beta=beta_disp,
        qty_a=trade.qty_b,
        qty_b=trade.qty_a,
        entry_price_a=trade.entry_price_b,
        entry_price_b=trade.entry_price_a,
        exit_price_a=trade.exit_price_b,
        exit_price_b=trade.exit_price_a,
        costs=trade.costs,
        exit_reason=trade.exit_reason,
        holding_days=trade.holding_days,
        pnl=trade.pnl,
    )


def _finite(value: float, fallback: float = 0.0) -> float:
    """Keep every reported number JSON-safe (no NaN or infinity)."""
    return float(value) if np.isfinite(value) else fallback


def _build_explanation(
    *,
    state: FinalState,
    ticker_a: str,
    ticker_b: str,
    suitability: rel.Suitability,
    metrics,
    signal: SignalStats | None,
) -> str:
    """One plain-English sentence saying what was decided and why."""
    if state == FinalState.UNSUITABLE_PAIR:
        reason = suitability.failures[0] if suitability.failures else "a suitability check failed"
        return f"{ticker_a} and {ticker_b} do not qualify as a tradeable pair because {reason}."
    if state == FinalState.HISTORICAL_SCREEN_FAILED:
        reason = _screen_failure_reason(metrics)
        return (
            f"{ticker_a} and {ticker_b} look related, but the fixed rule {reason} on the "
            "held-out evaluation dates, so no trade is proposed."
        )
    z_text = f"z = {signal.z_score:+.2f}" if signal is not None else "no z-score available"
    if state == FinalState.WAIT:
        return (
            f"{ticker_a} and {ticker_b} pass every check, but today's gap ({z_text}) is "
            f"below the {config.ENTRY_Z:.1f} entry threshold, so the strategy waits."
        )
    if state == FinalState.SELL_A_BUY_B:
        return (
            f"{ticker_a} looks unusually expensive relative to {ticker_b} ({z_text}), so "
            f"the strategy would sell {ticker_a} and buy {ticker_b}."
        )
    return (
        f"{ticker_a} looks unusually cheap relative to {ticker_b} ({z_text}), so the "
        f"strategy would buy {ticker_a} and sell {ticker_b}."
    )


def _screen_failure_reason(metrics) -> str:
    """The first backtest gate that failed, in gate order."""
    if metrics is None:
        return "could not be simulated"
    if metrics.n_trades < config.MIN_TRADES:
        return f"completed only {metrics.n_trades} trades (minimum {config.MIN_TRADES})"
    if metrics.net_profit <= 0:
        return "lost money after estimated costs"
    if metrics.profit_factor is not None and metrics.profit_factor <= config.MIN_PROFIT_FACTOR:
        return "saw its gross wins fail to outweigh its gross losses"
    if metrics.max_drawdown < config.MAX_DRAWDOWN_LIMIT:
        return (
            f"suffered a {metrics.max_drawdown:.0%} drawdown "
            f"(limit {config.MAX_DRAWDOWN_LIMIT:.0%})"
        )
    return "did not clear the minimum historical screen"
