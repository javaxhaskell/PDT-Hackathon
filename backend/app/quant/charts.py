"""Section 7 of the spec: chart series for the frontend.

Three charts, all with plain YYYY-MM-DD date strings and daily points
(no downsampling):

1. Normalised prices — both stocks rebased to 100 at the first common date.
2. Spread and signal — spread, rolling average, entry bands (mean +/-
   ENTRY_Z standard deviations) and stop bands (mean +/- STOP_Z), plus
   entry/exit markers from the trade ledger. Rolling series only exist
   where the previous-60-day window exists.
3. Backtest equity — the after-cost equity curve over the evaluation
   period, starting at 1.0.

All inputs arrive here already mapped to the user's DISPLAYED order (the
engine negates the spread series when the display order differs from the
canonical fit order).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app import config
from app.schemas import (
    Charts,
    EquityChart,
    NormalisedPricesChart,
    SeriesPoint,
    SpreadChart,
    SpreadMarker,
    TradeRecord,
)


def _point(date: str, value: float) -> SeriesPoint:
    return SeriesPoint(date=date, value=round(float(value), 6))


def build_charts(
    *,
    dates: pd.DatetimeIndex,
    close_a: np.ndarray,          # displayed ticker A adjusted closes
    close_b: np.ndarray,          # displayed ticker B adjusted closes
    spread: np.ndarray,           # displayed-sign spread, full sample
    rolling_mean: np.ndarray,     # displayed-sign previous-60 rolling mean (NaN early)
    rolling_std: np.ndarray,      # previous-60 rolling std (sign-free, NaN early)
    z: np.ndarray,                # displayed-sign z-scores (NaN early)
    trades: list[TradeRecord],    # displayed-order trade ledger
    formation_end: str,           # last formation date, YYYY-MM-DD
    equity_points: list[SeriesPoint],
) -> Charts:
    date_strings = [d.strftime("%Y-%m-%d") for d in dates]

    # --- 1) normalised prices: both stocks = 100 on the first common date ---
    normalised = NormalisedPricesChart(
        a=[
            _point(ds, 100.0 * c / close_a[0])
            for ds, c in zip(date_strings, close_a, strict=True)
        ],
        b=[
            _point(ds, 100.0 * c / close_b[0])
            for ds, c in zip(date_strings, close_b, strict=True)
        ],
    )

    # --- 2) spread chart with rolling bands where the window exists ---
    spread_series = [_point(ds, s) for ds, s in zip(date_strings, spread, strict=True)]
    mean_series: list[SeriesPoint] = []
    upper_entry: list[SeriesPoint] = []
    lower_entry: list[SeriesPoint] = []
    upper_stop: list[SeriesPoint] = []
    lower_stop: list[SeriesPoint] = []
    for ds, m, s in zip(date_strings, rolling_mean, rolling_std, strict=True):
        if not (np.isfinite(m) and np.isfinite(s)):
            continue
        mean_series.append(_point(ds, m))
        upper_entry.append(_point(ds, m + config.ENTRY_Z * s))
        lower_entry.append(_point(ds, m - config.ENTRY_Z * s))
        upper_stop.append(_point(ds, m + config.STOP_Z * s))
        lower_stop.append(_point(ds, m - config.STOP_Z * s))

    z_by_date = {
        ds: float(v) for ds, v in zip(date_strings, z, strict=True) if np.isfinite(v)
    }
    markers: list[SpreadMarker] = []
    for trade in trades:
        markers.append(
            SpreadMarker(
                date=trade.entry_date,
                kind="entry",
                direction=trade.direction,
                z=round(z_by_date.get(trade.signal_date, 0.0), 4),
            )
        )
        if trade.exit_date is not None:
            # End-of-sample exits have no exit signal; show the z at the exit date.
            z_date = trade.exit_signal_date or trade.exit_date
            markers.append(
                SpreadMarker(
                    date=trade.exit_date,
                    kind="exit",
                    direction=trade.direction,
                    z=round(z_by_date.get(z_date, 0.0), 4),
                )
            )

    spread_chart = SpreadChart(
        spread=spread_series,
        rolling_mean=mean_series,
        upper_entry=upper_entry,
        lower_entry=lower_entry,
        upper_stop=upper_stop,
        lower_stop=lower_stop,
        markers=markers,
        formation_end=formation_end,
    )

    # --- 3) after-cost equity over the evaluation period ---
    return Charts(
        normalised_prices=normalised,
        spread=spread_chart,
        equity=EquityChart(equity=equity_points),
    )
