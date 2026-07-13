"""Live yfinance providers for daily adjusted prices and recent news.

Conventions (documented and frozen):

- ``auto_adjust=True`` so BOTH Open and Close are adjusted consistently.
  A raw Open is never mixed with an adjusted Close.
- Currency and exchange come from ``fast_info`` with graceful fallbacks.
- Successful live responses are cached in-process for 15 minutes
  (``config.PRICE_CACHE_TTL_SECONDS`` / ``config.NEWS_CACHE_TTL_SECONDS``).
- A live failure raises a typed :class:`ProviderError`. It is NEVER
  silently replaced with fixture data — the UI must show a provider
  error and the user may explicitly switch to fixture mode.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pandas as pd
import yfinance

from app import config
from app.data.cache import TTLCache
from app.data.provider import (
    PriceHistory,
    ProviderError,
    canonicalise_url,
    filter_news_items,
)
from app.schemas import NewsItem

logger = logging.getLogger("pairscope.data.yfinance")


def _now_utc_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class YFinancePriceProvider:
    """Daily adjusted open/close prices from yfinance with a 15-minute cache."""

    def __init__(self) -> None:
        self._cache = TTLCache(config.PRICE_CACHE_TTL_SECONDS)

    def get_history(self, ticker: str, lookback: str) -> PriceHistory:
        symbol = ticker.strip().upper()
        cache_key = (symbol, lookback)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            yf_ticker = yfinance.Ticker(symbol)
            hist = yf_ticker.history(period=lookback, interval="1d", auto_adjust=True)
        except Exception as exc:
            logger.warning("yfinance history fetch failed for %s: %r", symbol, exc)
            raise ProviderError(
                f"Live price data could not be fetched for '{symbol}' "
                f"({type(exc).__name__}). The data source may be rate-limited or "
                "unreachable; try again shortly or use fixture mode.",
                ticker=symbol,
            ) from exc

        if hist is None or hist.empty:
            raise ProviderError(
                f"No price history was returned for '{symbol}'. The ticker may be "
                "invalid or delisted, or the data source may be temporarily unavailable.",
                ticker=symbol,
            )

        df = hist[["Open", "Close"]].rename(columns={"Open": "open", "Close": "close"})
        index = pd.DatetimeIndex(df.index)
        if index.tz is not None:
            index = index.tz_localize(None)
        df.index = index.normalize()
        df = df.sort_index()

        currency, exchange = self._fast_info(yf_ticker, symbol)
        history = PriceHistory(
            df=df,
            currency=currency,
            exchange=exchange,
            last_market_date=str(df.index[-1].date()),
            provider="yfinance",
            retrieved_at=_now_utc_iso(),
            is_fixture=False,
            fixture_captured_at=None,
        )
        self._cache.set(cache_key, history)
        return history

    @staticmethod
    def _fast_info(yf_ticker: yfinance.Ticker, symbol: str) -> tuple[str, str | None]:
        """Currency/exchange via fast_info; documented fallback to USD/None."""
        currency: str | None = None
        exchange: str | None = None
        try:
            info = yf_ticker.fast_info
            currency = getattr(info, "currency", None)
            exchange = getattr(info, "exchange", None)
        except Exception as exc:
            logger.info("fast_info unavailable for %s: %r", symbol, exc)
        if not currency:
            logger.info("currency missing for %s; falling back to USD", symbol)
            currency = "USD"
        return currency, exchange


class YFinanceNewsProvider:
    """Recent news metadata from ``Ticker.news`` mapped to ``NewsItem``.

    - Stable ``source_id`` of the form ``yf-<provider id>``.
    - URLs are canonicalised where practical (fragments/tracking stripped).
    - Deduped by provider id + normalised headline; capped at
      ``config.MAX_NEWS_ITEMS_PER_TICKER`` items within the last
      ``config.NEWS_LOOKBACK_DAYS`` calendar days. Items whose
      ``published_at`` cannot be parsed are kept but noted in the log.
    """

    def __init__(self) -> None:
        self._cache = TTLCache(config.NEWS_CACHE_TTL_SECONDS)

    def get_news(self, ticker: str) -> list[NewsItem]:
        symbol = ticker.strip().upper()
        cached = self._cache.get(symbol)
        if cached is not None:
            return cached

        try:
            raw = yfinance.Ticker(symbol).news or []
        except Exception as exc:
            logger.warning("yfinance news fetch failed for %s: %r", symbol, exc)
            raise ProviderError(
                f"Live news could not be fetched for '{symbol}' "
                f"({type(exc).__name__}). The quant analysis is unaffected.",
                ticker=symbol,
            ) from exc

        items = [item for entry in raw if (item := self._map_entry(symbol, entry)) is not None]
        usable = filter_news_items(items, as_of=datetime.now(UTC))
        self._cache.set(symbol, usable)
        return usable

    @staticmethod
    def _map_entry(symbol: str, entry: dict) -> NewsItem | None:
        content = entry.get("content", entry) or {}
        headline = content.get("title")
        if not headline:
            return None
        provider = content.get("provider") or {}
        url = None
        for key in ("canonicalUrl", "clickThroughUrl"):
            candidate = content.get(key)
            if isinstance(candidate, dict) and candidate.get("url"):
                url = candidate["url"]
                break
        stable_id = entry.get("id") or content.get("id") or headline[:24]
        return NewsItem(
            source_id=f"yf-{stable_id}",
            ticker=symbol,
            headline=headline,
            snippet=content.get("summary") or content.get("description") or None,
            source=provider.get("displayName") or "Yahoo Finance",
            published_at=content.get("pubDate") or content.get("displayTime") or "",
            url=canonicalise_url(url),
        )
