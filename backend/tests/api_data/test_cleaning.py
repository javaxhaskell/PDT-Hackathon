"""Unit tests for price cleaning, alignment and the staleness rule."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app import config
from app.data.cleaning import (
    align_pair,
    clean_price_frame,
    is_stale,
    min_required_observations,
)


def frame(dates: list[str], opens: list[float], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"open": opens, "close": closes}, index=pd.to_datetime(dates)
    )


class TestCleanPriceFrame:
    def test_sorts_and_drops_duplicate_dates(self):
        df = frame(
            ["2026-01-03", "2026-01-01", "2026-01-02", "2026-01-02"],
            [3.0, 1.0, 2.0, 99.0],
            [3.5, 1.5, 2.5, 99.5],
        )
        out = clean_price_frame(df)
        assert list(out.index) == list(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]))
        # First occurrence (after sorting) is kept for the duplicated date.
        assert out.loc[pd.Timestamp("2026-01-02"), "open"] == 2.0

    def test_drops_non_positive_prices(self):
        df = frame(
            ["2026-01-01", "2026-01-02", "2026-01-03"],
            [10.0, 0.0, -5.0],
            [10.5, 11.0, 12.0],
        )
        out = clean_price_frame(df)
        assert len(out) == 1
        assert out.index[0] == pd.Timestamp("2026-01-01")

    def test_drops_non_finite_prices(self):
        df = frame(
            ["2026-01-01", "2026-01-02", "2026-01-03"],
            [10.0, np.nan, 12.0],
            [10.5, 11.0, np.inf],
        )
        out = clean_price_frame(df)
        assert list(out.index) == [pd.Timestamp("2026-01-01")]

    def test_original_frame_not_mutated(self):
        df = frame(["2026-01-02", "2026-01-01"], [2.0, 1.0], [2.5, 1.5])
        clean_price_frame(df)
        assert list(df.index) == list(pd.to_datetime(["2026-01-02", "2026-01-01"]))


class TestAlignPair:
    def test_inner_join_on_common_dates(self):
        df_a = frame(["2026-01-01", "2026-01-02", "2026-01-03"], [1, 2, 3], [1, 2, 3])
        df_b = frame(["2026-01-02", "2026-01-03", "2026-01-04"], [4, 5, 6], [4, 5, 6])
        out_a, out_b = align_pair(df_a, df_b)
        expected = list(pd.to_datetime(["2026-01-02", "2026-01-03"]))
        assert list(out_a.index) == expected
        assert list(out_b.index) == expected
        assert out_a.loc[pd.Timestamp("2026-01-02"), "open"] == 2
        assert out_b.loc[pd.Timestamp("2026-01-02"), "open"] == 4

    def test_no_overlap_gives_empty_frames(self):
        df_a = frame(["2026-01-01"], [1], [1])
        df_b = frame(["2026-02-01"], [2], [2])
        out_a, out_b = align_pair(df_a, df_b)
        assert len(out_a) == 0 and len(out_b) == 0


class TestStaleness:
    """Conservative calendar-day rule: stale only when the last market date
    is MORE than config.STALE_CALENDAR_DAYS (7) calendar days before
    retrieval — weekends and ordinary public holidays never trigger it."""

    def test_exactly_at_limit_is_not_stale(self):
        as_of = datetime(2026, 7, 8, 15, 0, tzinfo=UTC)
        assert config.STALE_CALENDAR_DAYS == 7
        assert is_stale("2026-07-01", as_of) is False

    def test_one_day_past_limit_is_stale(self):
        as_of = datetime(2026, 7, 9, 15, 0, tzinfo=UTC)
        assert is_stale("2026-07-01", as_of) is True

    def test_weekend_gap_is_not_stale(self):
        # Friday close checked on Monday: 3 calendar days.
        as_of = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)  # Monday
        assert is_stale("2026-07-10", as_of) is False


class TestMinObservations:
    def test_one_year_needs_252(self):
        assert min_required_observations("1y") == config.MIN_OBS_ONE_YEAR == 252

    def test_longer_lookbacks_need_400(self):
        assert min_required_observations("2y") == config.MIN_OBS_LONGER == 400
        assert min_required_observations("3y") == 400
