"""Shared fixtures for data/AI/API tests.

The quant engine is built concurrently by another agent, so every test
overrides the lazy ``get_run_analysis`` seam with a deterministic fake
that returns a canned ``app.schemas.QuantResult``. Nothing in this
package imports ``app.quant``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ai import lens
from app.data.provider import PriceHistory, ProviderError
from app.schemas import (
    FinalState,
    NewsItem,
    QuantResult,
    SizingLeg,
    SizingResult,
)

# ---------------------------------------------------------------------------
# Deterministic fake quant engine (pure function of nothing but constants)
# ---------------------------------------------------------------------------


def fake_run_analysis(
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
    return QuantResult(
        state=FinalState.SELL_A_BUY_B,
        explanation="Deterministic fake quant result for tests.",
        sizing=SizingResult(
            sized=True,
            legs=[
                SizingLeg(ticker=ticker_a, side="SELL", shares=10, price=55.0, notional=550.0),
                SizingLeg(ticker=ticker_b, side="BUY", shares=4, price=140.0, notional=560.0),
            ],
            gross_exposure=1110.0,
            net_exposure=10.0,
            estimated_cost=1.11,
            stress_loss_estimate=33.3,
            risk_budget=100.0,
            max_gross_allowed=7500.0,
            remaining_cash=8890.0,
        ),
        warnings=["fake quant warning"],
    )


# ---------------------------------------------------------------------------
# Stub price provider
# ---------------------------------------------------------------------------


def make_history(
    ticker: str,
    *,
    n_days: int = 520,
    currency: str = "USD",
    exchange: str | None = "NYQ",
    end: str = "2026-07-10",
) -> PriceHistory:
    """Deterministic synthetic history ending at ``end`` (a Friday)."""
    index = pd.bdate_range(end=end, periods=n_days)
    base = 100.0 + (sum(map(ord, ticker)) % 7)  # deterministic offset per ticker
    opens = [base + 0.01 * i for i in range(n_days)]
    closes = [base + 0.01 * i + 0.005 for i in range(n_days)]
    df = pd.DataFrame({"open": opens, "close": closes}, index=index)
    last_date = str(index[-1].date())
    retrieved = (index[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%dT12:00:00+00:00")
    return PriceHistory(
        df=df,
        currency=currency,
        exchange=exchange,
        last_market_date=last_date,
        provider="stub",
        retrieved_at=retrieved,
        is_fixture=False,
        fixture_captured_at=None,
    )


class StubPriceProvider:
    def __init__(self, histories: dict[str, PriceHistory]):
        self._histories = {t.upper(): h for t, h in histories.items()}

    def get_history(self, ticker: str, lookback: str) -> PriceHistory:
        symbol = ticker.strip().upper()
        if symbol not in self._histories:
            raise ProviderError(f"stub has no data for '{symbol}'", ticker=symbol)
        return self._histories[symbol]


class StubNewsProvider:
    def __init__(self, news: dict[str, list[NewsItem]]):
        self._news = {t.upper(): items for t, items in news.items()}

    def get_news(self, ticker: str) -> list[NewsItem]:
        symbol = ticker.strip().upper()
        if symbol not in self._news:
            raise ProviderError(f"stub has no news for '{symbol}'", ticker=symbol)
        return self._news[symbol]


def make_news_item(
    ticker: str,
    idx: int,
    *,
    headline: str | None = None,
    days_ago: int = 1,
    as_of: datetime | None = None,
    source_id: str | None = None,
) -> NewsItem:
    anchor = as_of or datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    published = anchor - timedelta(days=days_ago)
    return NewsItem(
        source_id=source_id or f"yf-{ticker.lower()}-{idx}",
        ticker=ticker.upper(),
        headline=headline or f"{ticker.upper()} test headline number {idx}",
        snippet=f"Snippet for {ticker.upper()} item {idx}.",
        source="TestWire",
        published_at=published.isoformat(),
        url=f"https://example.com/{ticker.lower()}/{idx}",
    )


# ---------------------------------------------------------------------------
# App / client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_lens_cache():
    lens.clear_cache()
    yield
    lens.clear_cache()


@pytest.fixture()
def api():
    """The FastAPI app module with a fresh dependency-override table."""
    from app.api import main

    main.app.dependency_overrides.clear()
    main.app.dependency_overrides[main.get_run_analysis] = lambda: fake_run_analysis
    yield main
    main.app.dependency_overrides.clear()


@pytest.fixture()
def client(api):
    with TestClient(api.app, raise_server_exceptions=False) as test_client:
        yield test_client


def fixture_analyse_payload(**overrides) -> dict:
    payload = {
        "ticker_a": "KO",
        "ticker_b": "PEP",
        "starting_capital": 10_000.0,
        "risk_profile": "balanced",
        "lookback": "2y",
        "whole_shares": True,
        "cost_bps": 10.0,
        "data_mode": "fixture",
    }
    payload.update(overrides)
    return payload
