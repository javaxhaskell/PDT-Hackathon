"""Record frozen fixture snapshots from live provider responses.

Usage:
    .venv/bin/python scripts/record_fixtures.py
    .venv/bin/python scripts/record_fixtures.py --narrative ALL TRV

Writes prices_<TICKER>.json and news_<TICKER>.json into backend/fixtures/
for the demo pairs. With --narrative and a configured DEEPSEEK_API_KEY it
also records a real DeepSeek reply as narrative_<A>_<B>.json for the
offline demo (labelled "Recorded AI response" in the UI). Fixtures are
real recorded data — never hand-edited. The content hash covers both the
data and the metadata (minus the hash field itself).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yfinance

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
TICKERS = ["KO", "PEP", "NVDA", "ALL", "TRV"]
PERIOD = "3y"  # superset; shorter lookbacks slice from this


def canonical_hash(payload: object) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sealed(metadata: dict, payload_key: str, content: object) -> dict:
    """Stamp the content hash over metadata + content (matches _load_verified)."""
    metadata = dict(metadata)
    metadata["content_hash"] = canonical_hash({"metadata": metadata, payload_key: content})
    return {"metadata": metadata, payload_key: content}


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

    payload = sealed(
        {
            "ticker": ticker,
            "provider": "yfinance",
            "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "last_market_date": rows[-1]["date"],
            "currency": currency,
            "exchange": exchange,
            "auto_adjust": True,
        },
        "rows",
        rows,
    )
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
    payload = sealed(
        {
            "ticker": ticker,
            "provider": "yfinance",
            "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        "items",
        items,
    )
    out = FIXTURES_DIR / f"news_{ticker}.json"
    out.write_text(json.dumps(payload, indent=1))
    print(f"wrote {out.name}: {len(items)} items")


def record_narrative(ticker_a: str, ticker_b: str) -> None:
    """Record a REAL DeepSeek reply for the pair as narrative_<A>_<B>.json.

    Requires DEEPSEEK_API_KEY. The recorded file preserves the model name
    and capture time; the UI labels replays 'Recorded AI response'. This
    never fabricates a reply — without a key it refuses to record.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app import config
    from app.ai import lens
    from app.ai.deepseek import DeepSeekNarrativeProvider
    from app.data.fixture_provider import FixtureNewsProvider

    if not config.DEEPSEEK_API_KEY:
        raise SystemExit(
            "DEEPSEEK_API_KEY is not configured; refusing to record a narrative "
            "fixture (a recorded AI response must be real, never fabricated)."
        )
    a, b = ticker_a.strip().upper(), ticker_b.strip().upper()
    news = FixtureNewsProvider(FIXTURES_DIR)
    items_a, items_b = news.get_news(a), news.get_news(b)
    provider = DeepSeekNarrativeProvider()
    payload = lens.build_payload(a, items_a, b, items_b)
    completion = provider.complete(lens.SYSTEM_PROMPT, payload)

    out_payload = {
        "metadata": {
            "ticker_a": a,
            "ticker_b": b,
            "model": completion.model,
            "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "content_hash": canonical_hash(completion.reply),
        },
        "reply": completion.reply,
    }
    out = FIXTURES_DIR / f"narrative_{a}_{b}.json"
    out.write_text(json.dumps(out_payload, indent=1))
    print(f"wrote {out.name}: model={completion.model}")


if __name__ == "__main__":
    FIXTURES_DIR.mkdir(exist_ok=True)
    if len(sys.argv) >= 4 and sys.argv[1] == "--narrative":
        record_narrative(sys.argv[2], sys.argv[3])
        raise SystemExit(0)
    for ticker in TICKERS:
        try:
            record_prices(ticker)
            record_news(ticker)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED for {ticker}: {exc}", file=sys.stderr)
            raise
