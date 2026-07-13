"""Fixture provider: integrity verification, slicing and determinism."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.data.fixture_provider import (
    DEFAULT_FIXTURES_DIR,
    LOOKBACK_ROWS,
    FixtureNewsProvider,
    FixturePriceProvider,
)
from app.data.provider import ProviderError


@pytest.fixture()
def fixtures_copy(tmp_path) -> Path:
    for name in ("prices_KO.json", "news_KO.json"):
        shutil.copy(DEFAULT_FIXTURES_DIR / name, tmp_path / name)
    return tmp_path


class TestIntegrity:
    def test_corrupted_price_fixture_is_refused(self, fixtures_copy):
        path = fixtures_copy / "prices_KO.json"
        payload = json.loads(path.read_text())
        payload["rows"][0]["close"] = 999999.0  # hand-edited price
        path.write_text(json.dumps(payload))
        provider = FixturePriceProvider(fixtures_copy)
        with pytest.raises(ProviderError, match="integrity"):
            provider.get_history("KO", "2y")

    def test_corrupted_news_fixture_is_refused(self, fixtures_copy):
        path = fixtures_copy / "news_KO.json"
        payload = json.loads(path.read_text())
        payload["items"][0]["headline"] = "Fabricated headline"
        path.write_text(json.dumps(payload))
        provider = FixtureNewsProvider(fixtures_copy)
        with pytest.raises(ProviderError, match="integrity"):
            provider.get_news("KO")

    def test_intact_fixture_loads(self, fixtures_copy):
        history = FixturePriceProvider(fixtures_copy).get_history("KO", "2y")
        assert history.currency == "USD"


class TestUnknownTicker:
    def test_unknown_ticker_lists_available(self):
        provider = FixturePriceProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.get_history("TSLA", "2y")
        message = str(exc_info.value)
        for ticker in ("KO", "NVDA", "PEP"):
            assert ticker in message


class TestSlicing:
    """Lookbacks slice the MOST RECENT rows: 1y=252, 2y=504, 3y=756."""

    @pytest.mark.parametrize("lookback", ["1y", "2y", "3y"])
    def test_row_counts(self, lookback):
        history = FixturePriceProvider().get_history("KO", lookback)
        total_recorded = 752  # rows in the recorded 3y snapshot
        assert len(history.df) == min(LOOKBACK_ROWS[lookback], total_recorded)

    def test_slice_keeps_most_recent_rows(self):
        one_year = FixturePriceProvider().get_history("KO", "1y")
        three_year = FixturePriceProvider().get_history("KO", "3y")
        assert one_year.df.index[-1] == three_year.df.index[-1]
        assert one_year.last_market_date == three_year.last_market_date
        assert one_year.df.index[0] > three_year.df.index[0]


class TestDeterministicMetadata:
    def test_retrieved_at_equals_captured_at(self):
        history = FixturePriceProvider().get_history("KO", "2y")
        assert history.is_fixture is True
        assert history.retrieved_at == history.fixture_captured_at
        assert history.provider == "fixture"

    def test_dataframe_shape_and_order(self):
        history = FixturePriceProvider().get_history("KO", "2y")
        assert list(history.df.columns) == ["open", "close"]
        assert history.df.index.is_monotonic_increasing


class TestFixtureNews:
    def test_news_items_have_stable_ids_and_ticker(self):
        items = FixtureNewsProvider().get_news("KO")
        assert 2 <= len(items) <= 8
        assert all(item.source_id.startswith("yf-") for item in items)
        assert all(item.ticker == "KO" for item in items)

    def test_news_load_is_deterministic(self):
        first = FixtureNewsProvider().get_news("PEP")
        second = FixtureNewsProvider().get_news("PEP")
        assert [i.model_dump() for i in first] == [i.model_dump() for i in second]
