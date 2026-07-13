"""Section 5 of the spec: simple position sizing and risk.

The story a user can retell: use the line-of-best-fit ratio to split the
money between the two legs, fit the pair inside the money limit, then
scale it down if the stop could lose more than the risk allowance.

Two constraints, both from the risk profile in app.config:

- gross exposure  <= capital * max_gross_fraction
- stress estimate <= capital * max_stress_fraction

The stress estimate = |worst historical losing trade| (a fraction of
gross exposure) times the proposed gross exposure. Because both limits
cap gross exposure linearly, the largest allowed gross exposure is simply
the smaller of the two caps.

Short-sale proceeds are collateral, never spending money, so remaining
cash = capital - gross exposure. Works in CANONICAL ticker order; the
engine reorders the legs for display.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

from app import config
from app.schemas import SizingLeg, SizingResult

_EPS = 1e-9  # tolerance for floating-point comparisons against hard limits


def size_position(
    *,
    direction: str,          # canonical "SELL_A_BUY_B" or "BUY_A_SELL_B"
    ticker_a: str,           # canonical A
    ticker_b: str,           # canonical B
    beta: float,
    price_a: float,          # latest adjusted close of canonical A
    price_b: float,          # latest adjusted close of canonical B
    capital: float,
    profile_name: str,
    whole_shares: bool,
    cost_bps: float,
    worst_losing_pnl: float | None,  # most negative after-cost trade pnl, or None
) -> tuple[SizingResult, list[str]]:
    """Turn the 1-unit paper trade into share quantities inside the limits.

    Returns the sizing result plus any plain-English warnings (e.g. when
    the conservative stress fallback had to be used).
    """
    warnings: list[str] = []
    profile = config.RISK_PROFILES[profile_name]
    gross_limit = capital * profile["max_gross_fraction"]
    risk_budget = capital * profile["max_stress_fraction"]

    # Stress loss per unit of gross exposure: the worst historical losing
    # trade, or a conservative fallback when history contains no loser.
    if worst_losing_pnl is not None and worst_losing_pnl < 0:
        stress_fraction = abs(worst_losing_pnl)
    else:
        stress_fraction = config.STRESS_FALLBACK_FRACTION
        warnings.append(
            "No losing historical trade to base the stress estimate on; using a "
            f"conservative {config.STRESS_FALLBACK_FRACTION:.0%} of gross exposure instead."
        )

    # Largest gross exposure that satisfies BOTH the gross cap and the
    # stress budget (stress = stress_fraction * gross <= risk_budget).
    allowed_gross = min(gross_limit, risk_budget / stress_fraction)

    # Split the allowed money by the frozen hedge ratio.
    weight_a = 1.0 / (1.0 + beta)
    weight_b = beta / (1.0 + beta)
    target_notional_a = allowed_gross * weight_a
    target_notional_b = allowed_gross * weight_b

    def _unsized(reason: str) -> tuple[SizingResult, list[str]]:
        return (
            SizingResult(
                sized=False,
                reason=reason,
                legs=[],
                gross_exposure=0.0,
                net_exposure=0.0,
                estimated_cost=0.0,
                stress_loss_estimate=0.0,
                risk_budget=risk_budget,
                max_gross_allowed=gross_limit,
                remaining_cash=capital,
            ),
            warnings,
        )

    if whole_shares:
        pair = _whole_share_search(
            target_notional_a, target_notional_b, price_a, price_b, allowed_gross
        )
        if pair is None:
            return _unsized(
                "Even the smallest possible position (one share of each stock, about "
                f"{price_a + price_b:,.2f}) would exceed the {allowed_gross:,.2f} allowed by "
                f"your capital and the {profile_name} risk limits; add capital, pick a less "
                "conservative profile, or switch to fractional shares."
            )
        shares_a, shares_b = float(pair[0]), float(pair[1])
    else:
        shares_a = round(target_notional_a / price_a, config.FRACTIONAL_DECIMALS)
        shares_b = round(target_notional_b / price_b, config.FRACTIONAL_DECIMALS)
        if shares_a <= 0 or shares_b <= 0:
            return _unsized(
                "Your starting capital is too small to build both legs of the pair "
                "even with fractional shares."
            )
        # Rounding half-up can nudge the total a hair over the limit; if so,
        # round down instead so we never breach it.
        if shares_a * price_a + shares_b * price_b > allowed_gross * (1 + _EPS):
            scale = 10 ** config.FRACTIONAL_DECIMALS
            shares_a = math.floor(target_notional_a / price_a * scale) / scale
            shares_b = math.floor(target_notional_b / price_b * scale) / scale
            if shares_a <= 0 or shares_b <= 0:
                return _unsized(
                    "Your starting capital is too small to build both legs of the pair "
                    "even with fractional shares."
                )

    notional_a = shares_a * price_a
    notional_b = shares_b * price_b
    gross = notional_a + notional_b
    stress = stress_fraction * gross
    # Costs on all FOUR legs: both entry legs now, both exit legs later.
    # Exit prices are unknown, so the exit half is estimated at current
    # prices — the UI labels it as an estimate.
    estimated_cost = 2.0 * cost_bps * 1e-4 * gross

    side_a: Literal["BUY", "SELL"]
    side_b: Literal["BUY", "SELL"]
    if direction == "SELL_A_BUY_B":
        side_a, side_b = "SELL", "BUY"
        net_exposure = notional_b - notional_a  # buys minus sells
    else:
        side_a, side_b = "BUY", "SELL"
        net_exposure = notional_a - notional_b

    legs = [
        SizingLeg(ticker=ticker_a, side=side_a, shares=shares_a, price=price_a,
                  notional=notional_a),
        SizingLeg(ticker=ticker_b, side=side_b, shares=shares_b, price=price_b,
                  notional=notional_b),
    ]
    return (
        SizingResult(
            sized=True,
            reason=None,
            legs=legs,
            gross_exposure=gross,
            net_exposure=net_exposure,
            estimated_cost=estimated_cost,
            stress_loss_estimate=stress,
            risk_budget=risk_budget,
            max_gross_allowed=gross_limit,
            remaining_cash=capital - gross,
        ),
        warnings,
    )


def _whole_share_search(
    target_notional_a: float,
    target_notional_b: float,
    price_a: float,
    price_b: float,
    allowed_gross: float,
) -> tuple[int, int] | None:
    """Bounded search for the whole-share pair closest to the target ratio.

    Looks within WHOLE_SHARE_SEARCH_RADIUS shares of the rounded target
    quantities (never below one share per leg). A candidate is feasible
    when its gross exposure fits inside allowed_gross, which already folds
    in both the gross cap and the stress budget. Among feasible candidates
    we pick the one whose notional ratio is closest to the target ratio in
    log space; ties prefer the larger gross exposure (use more of the
    budget), then fewer A shares — fully deterministic.

    Returns None when not even one share of each stock fits.
    """
    radius = config.WHOLE_SHARE_SEARCH_RADIUS
    base_a = max(1, round(target_notional_a / price_a))
    base_b = max(1, round(target_notional_b / price_b))
    target_log_ratio = math.log(target_notional_a / target_notional_b)

    best: tuple[int, int] | None = None
    best_key: tuple[float, float, int] | None = None
    for qty_a in range(max(1, base_a - radius), base_a + radius + 1):
        for qty_b in range(max(1, base_b - radius), base_b + radius + 1):
            gross = qty_a * price_a + qty_b * price_b
            if gross > allowed_gross * (1 + _EPS):
                continue
            ratio_error = abs(math.log((qty_a * price_a) / (qty_b * price_b)) - target_log_ratio)
            # Quantise the error so mathematically identical ratios (e.g. 4/2
            # and 6/3 shares) compare as true ties instead of being separated
            # by floating-point noise; the tie then prefers the larger gross.
            key = (round(ratio_error, 9), -gross, qty_a)
            if best_key is None or key < best_key:
                best, best_key = (qty_a, qty_b), key

    if best is not None:
        return best
    # Last resort: the minimum feasible pair is one share of each leg.
    if price_a + price_b <= allowed_gross * (1 + _EPS):
        return (1, 1)
    return None


def worst_losing_pnl_from(pnls: list[float]) -> float | None:
    """The most negative after-cost trade pnl, or None when nothing lost money."""
    losses = [p for p in pnls if np.isfinite(p) and p < 0]
    return min(losses) if losses else None
