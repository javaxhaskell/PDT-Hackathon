"""Record frozen fixture snapshots from live yfinance responses.

Usage:
    .venv/bin/python scripts/record_fixtures.py

Writes prices_<TICKER>.json and news_<TICKER>.json into backend/fixtures/
for the demo pairs. Fixtures are real recorded data — never hand-edited.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
TICKERS = ["KO", "PEP", "NVDA"]
PERIOD = "3y"  # superset; shorter lookbacks slice from this


def canonical_hash(payload: object) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def record_prices(ticker: str) -> None:
    t = yfinance.Ticker(ticker)
    hist = t.history(period=PERIOD, interval="1d", auto_adjust=True)
    if hist.empty:
        raise SystemExit(f"no price data returned for {ticker}")
    info = t.fast_info
    currency = getattr(info, "currency", None) or "USD"
    exchange = getattr(info, "exchange", None)

    rows = []
    for date, row in hist.iterrows():
        o, c = float(row["Open"]), float(row["Close"])
        rows.append({"date": str(date.date()), "open": round(o, 6), "close": round(c, 6)})

    payload = {
        "metadata": {
            "ticker": ticker,
            "provider": "yfinance",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "last_market_date": rows[-1]["date"],
            "currency": currency,
            "exchange": exchange,
            "auto_adjust": True,
            "content_hash": canonical_hash(rows),
        },
        "rows": rows,
    }
    out = FIXTURES_DIR / f"prices_{ticker}.json"
    out.write_text(json.dumps(payload, indent=1))
    print(f"wrote {out.name}: {len(rows)} rows, last={rows[-1]['date']}, {currency}")


def record_news(ticker: str) -> None:
    t = yfinance.Ticker(ticker)
    raw = t.news or []
    items = []
    for entry in raw:
        content = entry.get("content", entry)
        headline = content.get("title")
        if not headline:
            continue
        provider = content.get("provider") or {}
        url = None
        for key in ("canonicalUrl", "clickThroughUrl"):
            u = content.get(key)
            if isinstance(u, dict) and u.get("url"):
                url = u["url"]
                break
        items.append(
            {
                "source_id": f"yf-{entry.get('id', content.get('id', headline[:24]))}",
                "headline": headline,
                "snippet": content.get("summary") or content.get("description") or None,
                "source": provider.get("displayName") or "Yahoo Finance",
                "published_at": content.get("pubDate") or content.get("displayTime") or "",
                "url": url,
            }
        )
    payload = {
        "metadata": {
            "ticker": ticker,
            "provider": "yfinance",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "content_hash": canonical_hash(items),
        },
        "items": items,
    }
    out = FIXTURES_DIR / f"news_{ticker}.json"
    out.write_text(json.dumps(payload, indent=1))
    print(f"wrote {out.name}: {len(items)} items")


if __name__ == "__main__":
    FIXTURES_DIR.mkdir(exist_ok=True)
    for ticker in TICKERS:
        try:
            record_prices(ticker)
            record_news(ticker)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED for {ticker}: {exc}", file=sys.stderr)
            raise
