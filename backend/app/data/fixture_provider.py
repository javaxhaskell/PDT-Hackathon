"""Deterministic fixture providers backed by frozen recorded snapshots.

Fixtures live in ``backend/fixtures`` (format: fixtures/README.md). They
are real recorded yfinance responses whose ``content_hash`` (SHA-256 of
the canonical JSON rows/items) is verified on every load; a corrupted or
hand-edited file is refused with a typed :class:`ProviderError`.

Lookback slicing (documented): the price fixtures store a ~3-year
superset and a request takes the MOST RECENT N rows —
1y = 252, 2y = 504, 3y = 756 trading rows (or every available row when
the fixture holds fewer). ``retrieved_at`` is deliberately set equal to
the fixture ``captured_at`` so fixture-mode responses are fully
deterministic and byte-identical across repeated requests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.data.provider import (
    PriceHistory,
    ProviderError,
    canonical_content_hash,
    filter_news_items,
    parse_published_at,
)
from app.schemas import NewsItem

DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

# Most-recent trading rows served per lookback (see module docstring).
LOOKBACK_ROWS = {"1y": 252, "2y": 504, "3y": 756}


def _load_verified(path: Path, payload_key: str, ticker: str) -> dict:
    """Load a fixture file and verify its content hash; refuse corruption.

    The hash covers BOTH the content array and the metadata (minus the
    hash field itself), so a tampered currency, capture time or exchange
    is refused just like tampered prices. Required metadata fields are
    validated here so a broken fixture fails with a clear message rather
    than a KeyError later.
    """
    try:
        payload = json.loads(path.read_text())
        metadata = payload["metadata"]
        content = payload[payload_key]
    except (OSError, ValueError, KeyError) as exc:
        raise ProviderError(
            f"Fixture file '{path.name}' could not be read or is malformed; "
            "refusing to use it.",
            ticker=ticker,
        ) from exc
    expected = metadata.get("content_hash")
    metadata_sans_hash = {k: v for k, v in metadata.items() if k != "content_hash"}
    hashed = canonical_content_hash({"metadata": metadata_sans_hash, payload_key: content})
    if not expected or hashed != expected:
        raise ProviderError(
            f"Fixture file '{path.name}' failed its integrity check (content hash "
            "mismatch). The file may be corrupted or hand-edited; refusing to use it.",
            ticker=ticker,
        )
    if not metadata.get("captured_at"):
        raise ProviderError(
            f"Fixture file '{path.name}' is missing its 'captured_at' metadata; "
            "re-record it with scripts/record_fixtures.py.",
            ticker=ticker,
        )
    return payload


class FixturePriceProvider:
    """Serves frozen recorded price snapshots for the demo tickers."""

    def __init__(self, fixtures_dir: Path | str | None = None):
        self._dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_FIXTURES_DIR

    def available_tickers(self) -> list[str]:
        return sorted(p.stem.removeprefix("prices_") for p in self._dir.glob("prices_*.json"))

    def get_history(self, ticker: str, lookback: str) -> PriceHistory:
        symbol = ticker.strip().upper()
        path = self._dir / f"prices_{symbol}.json"
        if not path.exists():
            available = ", ".join(self.available_tickers()) or "none"
            raise ProviderError(
                f"No fixture data is recorded for ticker '{symbol}'. "
                f"Available fixture tickers: {available}. "
                "Switch to live mode for other tickers.",
                ticker=symbol,
            )
        payload = _load_verified(path, "rows", symbol)
        metadata = payload["metadata"]

        n_rows = LOOKBACK_ROWS.get(lookback)
        if n_rows is None:
            raise ProviderError(
                f"Unknown lookback '{lookback}'. Supported lookbacks: "
                f"{', '.join(sorted(LOOKBACK_ROWS))}.",
                ticker=symbol,
            )
        rows = payload["rows"][-n_rows:]
        if not rows:
            raise ProviderError(
                f"Fixture file '{path.name}' contains no price rows.", ticker=symbol
            )

        df = pd.DataFrame(
            {
                "open": [row["open"] for row in rows],
                "close": [row["close"] for row in rows],
            },
            index=pd.to_datetime([row["date"] for row in rows]),
        ).sort_index()

        captured_at = metadata["captured_at"]
        return PriceHistory(
            df=df,
            currency=metadata["currency"],
            exchange=metadata.get("exchange"),
            last_market_date=rows[-1]["date"],
            provider="fixture",
            # Deterministic on purpose: retrieved_at == fixture captured_at.
            retrieved_at=captured_at,
            is_fixture=True,
            fixture_captured_at=captured_at,
        )


class FixtureNewsProvider:
    """Serves frozen recorded news snapshots, filtered relative to capture time."""

    def __init__(self, fixtures_dir: Path | str | None = None):
        self._dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_FIXTURES_DIR

    def get_news(self, ticker: str) -> list[NewsItem]:
        symbol = ticker.strip().upper()
        path = self._dir / f"news_{symbol}.json"
        if not path.exists():
            available = ", ".join(
                sorted(p.stem.removeprefix("news_") for p in self._dir.glob("news_*.json"))
            ) or "none"
            raise ProviderError(
                f"No fixture news is recorded for ticker '{symbol}'. "
                f"Available fixture tickers: {available}.",
                ticker=symbol,
            )
        payload = _load_verified(path, "items", symbol)
        items = [
            NewsItem(
                source_id=raw["source_id"],
                ticker=symbol,
                headline=raw["headline"],
                snippet=raw.get("snippet"),
                source=raw.get("source") or "Unknown",
                published_at=raw.get("published_at") or "",
                url=raw.get("url"),
            )
            for raw in payload["items"]
        ]
        # The 30-day recency window is anchored at the fixture capture time,
        # not the wall clock, so fixture mode stays deterministic forever.
        as_of = parse_published_at(payload["metadata"].get("captured_at"))
        return filter_news_items(items, as_of=as_of)
