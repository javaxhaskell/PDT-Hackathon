"""Step 3 of the PairScope model: how unusual is today's gap?

The spread is today's error from the frozen line of best fit. The z-score
expresses that error in units of its own recent variability: "how many
recent standard deviations away from normal are we today?"

STRICTLY NO LOOKAHEAD: every rolling statistic at date t uses only the
previous ROLLING_WINDOW spread values — the current date is always
excluded from its own window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app import config


def compute_spread(
    log_a: np.ndarray, log_b: np.ndarray, intercept: float, beta: float
) -> np.ndarray:
    """Spread over the FULL sample using the frozen formation fit.

    spread_t = log(price A at t) - intercept - beta * log(price B at t)

    A positive spread means A is expensive relative to its normal
    relationship with B; a negative spread means A is cheap.
    """
    return log_a - intercept - beta * log_b


def rolling_mean_std(spread: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Rolling mean and sample std (ddof=1) of the PREVIOUS window spreads.

    The .shift(1) is the no-lookahead guarantee: the window ending at t-1
    is what date t is compared against, so a value at date t never uses
    date t's own spread (or anything after it).
    """
    window = config.ROLLING_WINDOW
    mean = spread.rolling(window).mean().shift(1)
    std = spread.rolling(window).std(ddof=1).shift(1)
    return mean, std


def z_scores(spread: pd.Series) -> pd.Series:
    """z_t = (spread_t - mean of previous 60 spreads) / std of previous 60.

    Defined only once ROLLING_WINDOW prior spreads exist; NaN before that.
    A zero rolling std (flat spread) yields NaN rather than infinity.
    """
    mean, std = rolling_mean_std(spread)
    z = (spread - mean) / std
    return z.replace([np.inf, -np.inf], np.nan)


def mean_crossings(spread: pd.Series) -> int:
    """How many times the spread crossed its rolling average.

    We look at the deviation (spread minus previous-60 rolling mean) on
    every date where that rolling mean exists (formation tail plus the
    evaluation period) and count strict sign changes between consecutive
    dates. Exact zeros do not count as crossings. A healthy pair oscillates
    around its average instead of drifting away for good.
    """
    mean, _ = rolling_mean_std(spread)
    deviation = (spread - mean).dropna().to_numpy(dtype=float)
    if len(deviation) < 2:
        return 0
    return int(np.sum(deviation[1:] * deviation[:-1] < 0.0))
