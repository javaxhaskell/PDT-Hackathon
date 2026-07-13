"""Deterministic synthetic market data for the quant test suite.

Every generator is seeded, so identical calls always produce identical
frames — no network, no randomness between runs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.quant import run_analysis


def make_frames(
    log_a: np.ndarray, log_b: np.ndarray, seed: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Wrap two log-price paths into aligned open/close DataFrames.

    Opens are yesterday's close nudged by a tiny seeded overnight move, so
    open and close genuinely differ (needed to test next-open execution).
    """
    rng = np.random.default_rng(seed + 1_000_003)
    dates = pd.bdate_range("2020-01-02", periods=len(log_a))

    def frame(close: np.ndarray) -> pd.DataFrame:
        opens = np.empty_like(close)
        opens[0] = close[0]
        overnight = rng.normal(0.0, 0.001, len(close))
        opens[1:] = close[:-1] * np.exp(overnight[1:])
        return pd.DataFrame({"open": opens, "close": close}, index=dates)

    return frame(np.exp(log_a)), frame(np.exp(log_b))


def make_cointegrated_pair(
    n: int = 750,
    seed: int = 7,
    beta: float = 1.0,
    alpha: float = 0.5,
    phi: float = 0.90,
    walk_vol: float = 0.02,
    ou_vol: float = 0.006,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A related, mean-reverting pair: log A = alpha + beta*log B + AR(1) spread."""
    rng = np.random.default_rng(seed)
    log_b = np.log(60.0) + np.cumsum(rng.normal(0.0, walk_vol, n))
    noise = rng.normal(0.0, ou_vol, n)
    spread = np.zeros(n)
    for t in range(1, n):
        spread[t] = phi * spread[t - 1] + noise[t]
    log_a = alpha + beta * log_b + spread
    return make_frames(log_a, log_b, seed)


def make_independent_pair(n: int = 750, seed: int = 21) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two unrelated random walks — should fail the suitability filter."""
    rng = np.random.default_rng(seed)
    log_a = np.log(80.0) + np.cumsum(rng.normal(0.0, 0.02, n))
    log_b = np.log(40.0) + np.cumsum(rng.normal(0.0, 0.02, n))
    return make_frames(log_a, log_b, seed)


def make_low_correlation_pair(n: int = 750, seed: int = 33) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A weak shared factor drowned by independent noise: correlation well below 0.60."""
    rng = np.random.default_rng(seed)
    common = np.cumsum(rng.normal(0.0, 0.008, n))
    idio_a = np.cumsum(rng.normal(0.0, 0.02, n))
    idio_b = np.cumsum(rng.normal(0.0, 0.02, n))
    log_a = np.log(70.0) + common + idio_a
    log_b = np.log(50.0) + common + idio_b
    return make_frames(log_a, log_b, seed)


def make_changing_beta_pair(n: int = 750, seed: int = 11) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Beta jumps from 1 to 3 at the middle of the formation period.

    Returns stay highly correlated, but the two formation halves disagree
    about the hedge ratio by far more than the 50% limit.
    """
    rng = np.random.default_rng(seed)
    x = np.cumsum(rng.normal(0.0, 0.02, n))
    split = int(np.floor(n * 0.60))
    beta_t = np.where(np.arange(n) < split // 2, 1.0, 3.0)
    log_b = np.log(60.0) + x
    log_a = np.log(45.0) + beta_t * x + rng.normal(0.0, 0.001, n)
    return make_frames(log_a, log_b, seed)


def run(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    *,
    ticker_a: str = "AAA",
    ticker_b: str = "BBB",
    starting_capital: float = 10_000.0,
    risk_profile: str = "balanced",
    whole_shares: bool = True,
    cost_bps: float = 10.0,
):
    """run_analysis with test-friendly defaults."""
    return run_analysis(
        df_a,
        df_b,
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        starting_capital=starting_capital,
        risk_profile=risk_profile,
        whole_shares=whole_shares,
        cost_bps=cost_bps,
    )


def force_final_z(
    df_a: pd.DataFrame, df_b: pd.DataFrame, target_z: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rewrite the final close of A so the last-day z-score equals target_z.

    Only the last date changes, and the rolling window always excludes the
    current date, so every other statistic is untouched. Assumes the
    displayed order (AAA, BBB) is already canonical.
    """
    base = run(df_a, df_b)
    assert base.relationship is not None and base.signal is not None
    new_spread = base.signal.rolling_mean + target_z * base.signal.rolling_std
    log_b_last = np.log(df_b["close"].iloc[-1])
    new_close_a = np.exp(
        base.relationship.intercept + base.relationship.beta * log_b_last + new_spread
    )
    df_a2 = df_a.copy()
    df_a2.iloc[-1, df_a2.columns.get_loc("close")] = new_close_a
    return df_a2, df_b


@pytest.fixture(scope="session")
def good_pair() -> tuple[pd.DataFrame, pd.DataFrame]:
    return make_cointegrated_pair()


@pytest.fixture(scope="session")
def actionable_pair(good_pair) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The good pair with today's z forced to +2.5 (canonical A rich)."""
    return force_final_z(*good_pair, target_z=2.5)
