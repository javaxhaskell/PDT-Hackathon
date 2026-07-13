"""Steps 1-2 of the PairScope model: do the two stocks move together, and
what is their normal (line-of-best-fit) relationship?

Everything here is school-level statistics: the Pearson correlation of
daily percentage returns, and an ordinary least-squares straight line
between log prices. All thresholds come from app.config; nothing is
hard-coded here.

All functions in this module work in CANONICAL ticker order (alphabetical).
The engine maps results back to the user's displayed order.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app import config

# A ratio we cannot compute (e.g. dividing by a zero beta) is reported as
# this large-but-finite sentinel so JSON stays serialisable. Any sentinel
# value always fails its threshold check.
UNDEFINED_RATIO = 999.0


def daily_returns(close: pd.Series) -> pd.Series:
    """Daily percentage move: today's close divided by yesterday's close, minus 1."""
    return close.pct_change().dropna()


def return_correlation(close_a: pd.Series, close_b: pd.Series) -> float:
    """Pearson correlation of the two daily-return series over the FULL sample.

    This asks: when stock A moves 1% in a day, does stock B tend to move the
    same way? It is only a first filter — correlation alone is never an edge.
    Returns NaN when a correlation cannot be computed (e.g. a flat series);
    a NaN always fails the suitability check downstream.
    """
    ra = daily_returns(close_a).to_numpy(dtype=float)
    rb = daily_returns(close_b).to_numpy(dtype=float)
    if len(ra) < 2 or len(rb) < 2 or len(ra) != len(rb):
        return float("nan")
    if float(np.std(ra)) == 0.0 or float(np.std(rb)) == 0.0:
        return float("nan")  # a flat price series has no co-movement to measure
    return float(np.corrcoef(ra, rb)[0, 1])


def formation_split(n_obs: int) -> int:
    """Row index where the evaluation period starts.

    The first FORMATION_FRACTION (60%) of common dates — floored, so the
    formation period never exceeds 60% — is used to fit the relationship.
    The remaining dates are held out for honest, out-of-sample evaluation.
    """
    return int(np.floor(n_obs * config.FORMATION_FRACTION))


def ols_fit(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    """Plain line of best fit y = intercept + beta * x, via least squares.

    Returns (intercept, beta). Beta is the relative percentage sensitivity
    of stock A to stock B (because both series are log prices).
    """
    if len(y) < 3 or len(x) < 3:
        return float("nan"), float("nan")
    design = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(coef[0]), float(coef[1])


@dataclass(frozen=True)
class RelationshipFit:
    """The frozen formation-period relationship between the two log prices."""

    correlation: float          # full-sample daily-return correlation
    intercept: float            # formation OLS intercept
    beta: float                 # formation OLS slope (hedge ratio)
    beta_h1: float              # beta fit on the first half of the formation period
    beta_h2: float              # beta fit on the second half
    split_beta_change: float    # |beta_h1 - beta_h2| / |beta|
    leg_weight_a: float         # 1 / (1 + beta): A's share of gross exposure
    leg_weight_b: float         # beta / (1 + beta): B's share of gross exposure
    eval_start_idx: int         # first evaluation row; formation is rows [0, split)

    @property
    def beta_valid(self) -> bool:
        """A usable hedge ratio must be a finite, strictly positive number."""
        return bool(np.isfinite(self.beta) and self.beta > 0.0)


def fit_relationship(close_a: pd.Series, close_b: pd.Series) -> RelationshipFit:
    """Fit the formation-period OLS line and its stability diagnostics.

    Uses only the first 60% of common dates for the fit, then re-fits each
    half of that window separately to ask: did the balancing ratio change
    dramatically while we were learning it?
    """
    n = len(close_a)
    split = formation_split(n)
    log_a = np.log(close_a.to_numpy(dtype=float))
    log_b = np.log(close_b.to_numpy(dtype=float))

    intercept, beta = ols_fit(log_a[:split], log_b[:split])

    half = split // 2
    _, beta_h1 = ols_fit(log_a[:half], log_b[:half])
    _, beta_h2 = ols_fit(log_a[half:split], log_b[half:split])

    if np.isfinite(beta_h1) and np.isfinite(beta_h2) and np.isfinite(beta) and abs(beta) > 1e-12:
        split_change = min(abs(beta_h1 - beta_h2) / abs(beta), UNDEFINED_RATIO)
    else:
        split_change = UNDEFINED_RATIO

    if np.isfinite(beta) and abs(1.0 + beta) > 1e-12:
        leg_weight_a = 1.0 / (1.0 + beta)
        leg_weight_b = beta / (1.0 + beta)
    else:
        leg_weight_a = 0.0
        leg_weight_b = 0.0

    return RelationshipFit(
        correlation=return_correlation(close_a, close_b),
        intercept=intercept,
        beta=beta,
        beta_h1=float(beta_h1) if np.isfinite(beta_h1) else float("nan"),
        beta_h2=float(beta_h2) if np.isfinite(beta_h2) else float("nan"),
        split_beta_change=float(split_change),
        leg_weight_a=float(leg_weight_a),
        leg_weight_b=float(leg_weight_b),
        eval_start_idx=split,
    )


@dataclass(frozen=True)
class Suitability:
    """Results of the five pair-suitability safeguards, in spec order."""

    corr_ok: bool
    beta_ok: bool
    split_ok: bool
    leg_ok: bool
    crossings_ok: bool
    failures: list[str]  # plain-English reasons, in spec 4.6 order

    @property
    def passed(self) -> bool:
        return not self.failures


def check_suitability(fit: RelationshipFit, mean_crossings: int) -> Suitability:
    """Apply the five safeguards from spec section 4.6, in order.

    1. Daily-return correlation at least MIN_CORRELATION.
    2. Beta finite and positive (supports the intuitive trade direction).
    3. Beta stable across the two halves of the formation period.
    4. Neither leg dominates gross exposure.
    5. The spread actually oscillates around its rolling average.
    """
    corr_ok = bool(np.isfinite(fit.correlation) and fit.correlation >= config.MIN_CORRELATION)
    beta_ok = fit.beta_valid
    split_ok = bool(fit.split_beta_change <= config.MAX_SPLIT_BETA_CHANGE)
    max_leg = max(fit.leg_weight_a, fit.leg_weight_b)
    leg_ok = bool(max_leg <= config.MAX_LEG_WEIGHT)
    crossings_ok = bool(mean_crossings >= config.MIN_MEAN_CROSSINGS)

    failures: list[str] = []
    if not corr_ok:
        shown = fit.correlation if np.isfinite(fit.correlation) else 0.0
        failures.append(
            f"their daily-return correlation of {shown:.2f} is below the "
            f"{config.MIN_CORRELATION:.2f} minimum"
        )
    if not beta_ok:
        failures.append(
            f"the fitted hedge ratio (beta = {fit.beta:.2f}) is not a positive finite number"
        )
    if beta_ok and not split_ok:
        failures.append(
            f"beta changed {fit.split_beta_change:.0%} between the two halves of the "
            f"formation period (limit {config.MAX_SPLIT_BETA_CHANGE:.0%})"
        )
    if beta_ok and not leg_ok:
        failures.append(
            f"one leg would be {max_leg:.0%} of gross exposure "
            f"(limit {config.MAX_LEG_WEIGHT:.0%})"
        )
    if not crossings_ok:
        failures.append(
            f"the spread crossed its rolling average only {mean_crossings} times "
            f"(minimum {config.MIN_MEAN_CROSSINGS})"
        )

    return Suitability(
        corr_ok=corr_ok,
        beta_ok=beta_ok,
        split_ok=split_ok,
        leg_ok=leg_ok,
        crossings_ok=crossings_ok,
        failures=failures,
    )
