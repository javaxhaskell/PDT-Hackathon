"""Price cleaning, alignment and data-quality validation.

All rules follow spec section 4.1:

- sort by date, drop duplicate dates (first occurrence kept),
- drop rows with non-finite or non-positive open/close prices,
- align both stocks to common trading dates (inner join),
- require at least 252 common observations for a 1-year request and at
  least 400 for longer requests (values from config),
- staleness uses a conservative CALENDAR-DAY rule: exchange holiday
  calendars are out of scope, so data counts as stale only when the last
  market date is more than ``config.STALE_CALENDAR_DAYS`` (7) calendar
  days before the retrieval time. That comfortably allows weekends and
  ordinary public holidays without false alarms.
"""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd

from app import config


def clean_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by date, drop duplicate dates, drop non-finite/non-positive prices."""
    out = df.copy()
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="first")]
    finite = np.isfinite(out["open"]) & np.isfinite(out["close"])
    positive = (out["open"] > 0) & (out["close"] > 0)
    return out[finite & positive]


def align_pair(df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inner-join both frames onto their common trading dates (ascending)."""
    common = df_a.index.intersection(df_b.index).sort_values()
    return df_a.loc[common], df_b.loc[common]


def min_required_observations(lookback: str) -> int:
    """252 common observations for a 1-year request, 400 for longer ones."""
    return config.MIN_OBS_ONE_YEAR if lookback == "1y" else config.MIN_OBS_LONGER


def is_stale(last_market_date: str, as_of: datetime | date) -> bool:
    """Conservative calendar-day staleness rule (see module docstring).

    Stale only when strictly more than ``config.STALE_CALENDAR_DAYS``
    calendar days separate the last market date from ``as_of``.
    """
    last = date.fromisoformat(last_market_date[:10])
    as_of_date = as_of.date() if isinstance(as_of, datetime) else as_of
    return (as_of_date - last).days > config.STALE_CALENDAR_DAYS
