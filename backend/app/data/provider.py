"""Provider abstractions for the PairScope data layer.

Defines the frozen ``PriceHistory`` container and the ``PriceProvider`` /
``NewsProvider`` protocols from docs/INTERFACES.md, the typed
``ProviderError`` used to surface data failures as the PROVIDER_ERROR
final state (never a silent fixture fallback), and shared news utilities
(canonical hashing, URL canonicalisation, dedupe + recency filtering).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from app import config
from app.schemas import NewsItem

logger = logging.getLogger("pairscope.data")


class ProviderError(Exception):
    """A data provider could not supply usable data.

    The message is plain English and safe to show to the user. The API
    layer maps this to the PROVIDER_ERROR final state. A live error must
    never be silently replaced with fixture data — raising this is the
    only correct failure path.
    """

    def __init__(self, message: str, *, ticker: str | None = None):
        super().__init__(message)
        self.ticker = ticker


@dataclass
class PriceHistory:
    """Daily adjusted open/close history for one ticker (see INTERFACES.md)."""

    df: pd.DataFrame  # DatetimeIndex ascending, columns "open"/"close" (adjusted)
    currency: str
    exchange: str | None
    last_market_date: str  # YYYY-MM-DD
    provider: str  # "yfinance" | "fixture"
    retrieved_at: str  # ISO-8601 UTC
    is_fixture: bool
    fixture_captured_at: str | None = None
    currency_guessed: bool = False  # provider reported no currency; USD assumed


class PriceProvider(Protocol):
    def get_history(self, ticker: str, lookback: str) -> PriceHistory: ...


class NewsProvider(Protocol):
    def get_news(self, ticker: str) -> list[NewsItem]: ...


# ---------------------------------------------------------------------------
# Fixture hashing (must match backend/scripts/record_fixtures.py exactly)
# ---------------------------------------------------------------------------


def canonical_content_hash(payload: object) -> str:
    """SHA-256 of the canonical JSON encoding used when fixtures were recorded."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# News utilities (shared by live provider, fixture provider and the lens)
# ---------------------------------------------------------------------------

_TRACKING_PARAMS_PREFIXES = ("utm_", "gclid", "fbclid", "mc_cid", "mc_eid")


def canonicalise_url(url: str | None) -> str | None:
    """Best-effort URL canonicalisation: drop fragments and tracking params."""
    if not url:
        return None
    try:
        scheme, netloc, path, query, _fragment = urlsplit(url)
        kept = [
            (k, v)
            for k, v in parse_qsl(query, keep_blank_values=True)
            if not any(k.lower().startswith(p) for p in _TRACKING_PARAMS_PREFIXES)
        ]
        return urlunsplit((scheme, netloc.lower(), path, urlencode(kept), ""))
    except (ValueError, TypeError):
        return url


def normalise_headline(headline: str) -> str:
    """Lowercase, strip punctuation and collapse whitespace for dedupe keys."""
    text = re.sub(r"[^a-z0-9\s]", "", headline.lower())
    return re.sub(r"\s+", " ", text).strip()


def parse_published_at(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp; return None when unparsable."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def filter_news_items(
    items: list[NewsItem],
    *,
    as_of: datetime | None = None,
    max_items: int | None = None,
    window_days: int | None = None,
) -> list[NewsItem]:
    """Select the usable news items for one ticker.

    - Deduplicates by stable provider id AND by normalised headline.
    - Keeps only items published within ``window_days`` calendar days of
      ``as_of``. When ``as_of`` is None it defaults to the newest parsed
      ``published_at`` among the supplied items (deterministic for
      fixtures) and falls back to the current UTC time.
    - Items with an unparsable ``published_at`` are DROPPED (the spec
      requires items from the last 30 calendar days, and an undated item
      cannot prove it qualifies); each drop is logged.
    - Returns at most ``max_items`` items, newest first (deterministic
      tie-break on source_id).
    """
    max_items = config.MAX_NEWS_ITEMS_PER_TICKER if max_items is None else max_items
    window_days = config.NEWS_LOOKBACK_DAYS if window_days is None else window_days

    parsed: list[tuple[NewsItem, datetime | None]] = [
        (item, parse_published_at(item.published_at)) for item in items
    ]
    if as_of is None:
        dated = [dt for _, dt in parsed if dt is not None]
        as_of = max(dated) if dated else datetime.now(UTC)
    elif as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    parsed.sort(
        key=lambda p: (
            p[1] is None,
            -(p[1].timestamp()) if p[1] is not None else 0.0,
            p[0].source_id,
        )
    )

    window = timedelta(days=window_days)
    kept: list[NewsItem] = []
    seen_ids: set[str] = set()
    seen_headlines: set[str] = set()
    for item, dt in parsed:
        if len(kept) >= max_items:
            break
        if dt is None:
            logger.info(
                "news item %s has an unparsable published_at; dropping it "
                "(cannot verify the %s-day window)",
                item.source_id,
                window_days,
            )
            continue
        if (as_of - dt) > window:
            continue
        headline_key = normalise_headline(item.headline)
        if item.source_id in seen_ids or headline_key in seen_headlines:
            continue
        seen_ids.add(item.source_id)
        seen_headlines.add(headline_key)
        kept.append(item)
    return kept
