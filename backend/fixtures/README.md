# Fixture data format (frozen)

Fixtures are **frozen snapshots of real provider responses**. They are
recorded by `backend/scripts/record_fixtures.py` and must never be
hand-edited — especially not to manufacture a passing result.

## Price fixtures: `prices_<TICKER>.json`

```json
{
  "metadata": {
    "ticker": "KO",
    "provider": "yfinance",
    "captured_at": "2026-07-13T12:00:00+00:00",
    "last_market_date": "2026-07-10",
    "currency": "USD",
    "exchange": "NYQ",
    "auto_adjust": true,
    "content_hash": "sha256:..."
  },
  "rows": [
    {"date": "2023-07-13", "open": 55.12, "close": 55.60}
  ]
}
```

- Prices are daily **adjusted** Open/Close (`auto_adjust=True`), matching
  the live provider convention exactly.
- `content_hash` is the SHA-256 of the canonical JSON of `rows`; the
  fixture provider verifies it on load and refuses corrupted files.

## News fixtures: `news_<TICKER>.json`

```json
{
  "metadata": {
    "ticker": "KO",
    "provider": "yfinance",
    "captured_at": "2026-07-13T12:00:00+00:00",
    "content_hash": "sha256:..."
  },
  "items": [
    {
      "source_id": "yf-abc123",
      "headline": "...",
      "snippet": "...",
      "source": "Reuters",
      "published_at": "2026-07-09T14:00:00+00:00",
      "url": "https://..."
    }
  ]
}
```

## Recorded AI response: `narrative_<A>_<B>.json`

An optional frozen DeepSeek response for the offline demo. Preserves the
model name and capture time. The UI labels it **Recorded AI response**,
never live AI.

## Recorded pairs

- `ALL` / `TRV` — the candidate pair used in the demo (passed the full
  screen with an actionable signal at capture time).
- `NVDA` / `KO` — an unsuitable pair (used to demo honest rejection).
- `KO` / `PEP` — a borderline rejection (correlation just below the 0.60
  threshold at capture time — a good honesty story).

Fixture mode shows a visible **Recorded market snapshot** banner in the UI
and `is_fixture: true` plus `fixture_captured_at` in API metadata. Live
errors are never silently replaced with fixture data.
