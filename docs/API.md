# PairScope API contract

This document describes every HTTP endpoint exposed by the PairScope backend
(FastAPI, default `http://localhost:8000`). It is generated from the frozen
Pydantic contracts in `backend/app/schemas/contracts.py` and the frozen
thresholds in `backend/app/config.py` (methodology version **1.0.0**).
Interactive OpenAPI docs are served at `/docs` when the backend is running.

> **Single source of truth.** The backend is the only source of truth for the
> quant logic. The frontend renders the returned state and values exactly as
> received — it never recalculates, never re-derives a verdict, and never
> overrides a decision. Contract mismatches are resolved in the schemas, not
> with frontend workarounds.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness + whether DeepSeek is configured |
| GET | `/api/symbols/search?q=` | Ticker search / autocomplete |
| GET | `/api/methodology` | Every frozen threshold, for display in the UI |
| POST | `/api/analyse` | Full quant analysis of a pair |
| POST | `/api/narrative` | AI Narrative Lens for a pair (independent call) |

`POST /api/analyse` returns the **complete quant result without waiting for
DeepSeek**. When the Narrative Lens toggle is on, the frontend then calls
`POST /api/narrative` independently so the AI card can load without blocking
the main analysis. The narrative result can never alter the backtest, the
z-score, the trade direction or the share quantities.

---

## GET /api/health

No parameters.

**Response — `HealthResponse`**

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | `"ok"` | The API is up |
| `version` | string | Methodology/app version (e.g. `"1.0.0"`) |
| `deepseek_configured` | bool | `DEEPSEEK_API_KEY` is present server-side |

`deepseek_configured: true` means a key is configured; it does not prove the
live integration works. Reachability is only demonstrated by a real DeepSeek
request succeeding (surfaced per-call through `ai_status` on
`POST /api/narrative`). The API key is never exposed to the browser.

```json
{ "status": "ok", "version": "1.0.0", "deepseek_configured": true }
```

---

## GET /api/symbols/search?q=

Query parameter `q` — a partial ticker or company name. Direct ticker entry
always works even if search returns nothing.

**Response — `SymbolSearchResponse`**

| Field | Type | Meaning |
| --- | --- | --- |
| `results` | `SymbolSearchResult[]` | Matching symbols |

**`SymbolSearchResult`**

| Field | Type | Meaning |
| --- | --- | --- |
| `symbol` | string | Ticker symbol |
| `name` | string | Company name |
| `exchange` | string \| null | Exchange code |
| `currency` | string \| null | Quote currency |

```json
{ "results": [ { "symbol": "KO", "name": "The Coca-Cola Company", "exchange": "NYQ", "currency": "USD" } ] }
```

---

## GET /api/methodology

No parameters. Returns a serialisable snapshot of **every frozen threshold**
from `backend/app/config.py`, so the UI can display the values it uses and
judges can audit them. Top-level keys:

| Key | Contents |
| --- | --- |
| `methodology_version` | `"1.0.0"` |
| `data` | `min_obs_one_year` (252), `min_obs_longer` (400), `price_cache_ttl_seconds` (900), `stale_calendar_days` (7) |
| `correlation` | `min_correlation` (0.60) |
| `relationship` | `formation_fraction` (0.60), `max_leg_weight` (0.80), `min_mean_crossings` (6), `max_split_beta_change` (0.50) |
| `signal` | `rolling_window` (60), `entry_z` (2.0), `exit_z` (0.5), `stop_z` (3.5), `max_holding_days` (20) |
| `backtest_gate` | `min_trades` (5), `limited_evidence_trades` (10), `min_profit_factor` (1.0), `max_drawdown_limit` (−0.20), `default_cost_bps` (10.0) |
| `sizing` | `risk_profiles`, `stress_fallback_fraction` (0.03), `fractional_decimals` (4), `whole_share_search_radius` (3) |
| `narrative` | `max_news_items_per_ticker` (8), `news_lookback_days` (30), `min_usable_news_items` (2), `max_evidence_claims` (3), `max_explanation_words` (70), `model_env` |

Risk profiles (fraction of starting capital):

| Profile | Max gross exposure | Max stress loss |
| --- | ---: | ---: |
| `conservative` | 50% | 0.5% |
| `balanced` | 75% | 1.0% |
| `aggressive` | 100% | 2.0% |

---

## POST /api/analyse

### Request — `AnalyseRequest`

| Field | Type | Default | Validation | Meaning |
| --- | --- | --- | --- | --- |
| `ticker_a` | string | — (required) | 1–12 chars | Displayed stock A |
| `ticker_b` | string | — (required) | 1–12 chars | Displayed stock B |
| `starting_capital` | number | `10000.0` | > 0 | Starting capital in the pair's currency |
| `risk_profile` | enum | `"balanced"` | `conservative` \| `balanced` \| `aggressive` | Gross-exposure and stress-loss limits |
| `lookback` | enum | `"2y"` | `1y` \| `2y` \| `3y` | History window |
| `whole_shares` | bool | `true` | — | Whole shares vs fractional (4 dp) |
| `cost_bps` | number | `10.0` | 0–200 | Estimated cost in basis points **per leg per transaction** |
| `data_mode` | enum | `"live"` | `live` \| `fixture` | Live yfinance or recorded fixture snapshot |

The engine canonicalises the two tickers alphabetically internally before
fitting, then maps every output (directions, signs, legs, cards, charts) back
to the user's displayed A/B order. Callers always see displayed-order results.

### Response — `AnalyseResponse`

| Field | Type | Meaning |
| --- | --- | --- |
| `request` | `AnalyseRequest` | Echo of the request as parsed (defaults filled in) |
| `data` | `DataMetadata` \| null | Provider metadata; null when the provider failed before data existed |
| `state` | `FinalState` | Exactly one machine-readable verdict (see below) |
| `explanation` | string | One plain-English sentence explaining the verdict |
| `relationship` | `RelationshipStats` \| null | Correlation, beta, intercept, stability checks |
| `signal` | `SignalStats` \| null | Current spread, rolling stats, z-score (null only if the evaluation window is too short) |
| `backtest` | `BacktestMetrics` \| null | Every historical-screen metric |
| `trades` | `TradeRecord[]` | The shared trade ledger (equity/return/drawdown derive from it) |
| `sizing` | `SizingResult` \| null | Proposed paper-trade sizing, when appropriate |
| `evidence_cards` | `EvidenceCard[]` | The four evidence cards (all four whenever stats exist) |
| `charts` | `Charts` \| null | Normalised prices, spread + bands + markers, equity |
| `warnings` | string[] | Assumptions, limitations and data caveats to display |
| `methodology_version` | string | e.g. `"1.0.0"` |

### `FinalState` — every value and its meaning

| Value | Meaning |
| --- | --- |
| `INSUFFICIENT_DATA` | Too few common observations (fewer than 252 for a 1-year request, fewer than 400 for longer), or the usable window is too short to compute the required statistics |
| `UNSUITABLE_PAIR` | The pair fails a suitability check: identical tickers, different quoted currencies, correlation below 0.60, beta not finite or not positive, formation-half betas differing by more than 50% of the full-formation beta, a leg above 80% of gross exposure, or fewer than 6 spread/rolling-mean crossings |
| `HISTORICAL_SCREEN_FAILED` | The fixed rule failed the minimum historical screen on unseen evaluation dates after costs (fewer than 5 completed trades, net profit ≤ 0, profit factor ≤ 1.0, or max drawdown worse than −20%) |
| `WAIT` | The pair is suitable and the screen passed, but the current absolute z-score is below the 2.0 entry threshold — no unusual gap today |
| `BUY_A_SELL_B` | z-score ≤ −2.0: A looks unusually **cheap** relative to B, so the paper trade buys A and sells B |
| `SELL_A_BUY_B` | z-score ≥ +2.0: A looks unusually **expensive** relative to B, so the paper trade sells A and buys B |
| `PROVIDER_ERROR` | The data provider failed or returned invalid/stale data; nothing was analysed |

### Decision order (spec §4.6 — evaluated top to bottom, first match wins)

1. Provider or validation failure → `PROVIDER_ERROR`
2. Insufficient common data → `INSUFFICIENT_DATA`
3. Unsuitable pair — correlation below 0.60, invalid beta, beta changing by
   more than 50% between formation halves, a leg above 80%, or mean crossings
   below 6 (identical tickers and currency mismatch are decided upstream by
   the data layer) → `UNSUITABLE_PAIR`
4. Backtest gate failed → `HISTORICAL_SCREEN_FAILED`
5. Current absolute z-score below 2.0 → `WAIT`
6. Otherwise the direction implied by the z-score → `SELL_A_BUY_B` (z ≥ +2.0)
   or `BUY_A_SELL_B` (z ≤ −2.0)

Domain-level failure states (`PROVIDER_ERROR`, `INSUFFICIENT_DATA`,
`UNSUITABLE_PAIR`) are returned as HTTP 200 with the state in the body so the
UI can render the verdict and its explanation. Malformed request bodies fail
Pydantic validation (HTTP 422). Unexpected server faults return the `ApiError`
envelope — never a raw stack trace.

### `DataMetadata`

| Field | Type | Meaning |
| --- | --- | --- |
| `provider` | string | `"yfinance"` or `"fixture"` |
| `retrieved_at` | string | ISO-8601 UTC retrieval time |
| `last_market_date` | string | `YYYY-MM-DD` of the latest common session |
| `currency` | string | Common quote currency (pairs must match) |
| `n_common_observations` | int | Common trading dates after cleaning/alignment |
| `is_fixture` | bool | `true` → UI shows the **Recorded market snapshot** banner |
| `fixture_captured_at` | string \| null | ISO-8601 capture time, fixture mode only |
| `exchange_a` / `exchange_b` | string \| null | Exchange codes (a warning is added when they differ) |

Live responses are cached 15 minutes. Live errors are **never** silently
replaced with fixture data; fixture mode is always explicit and labelled.

### `RelationshipStats`

| Field | Type | Meaning |
| --- | --- | --- |
| `correlation` | number | Pearson correlation of daily returns (threshold ≥ 0.60) |
| `beta` | number | OLS slope of log A on log B over the formation period — the hedge ratio (a notional weight, not a share ratio) |
| `intercept` | number | OLS intercept over the formation period |
| `split_beta_change` | number | \|β_h1 − β_h2\| / \|β_full\| across formation halves (limit 0.50) |
| `mean_crossings` | int | Times the spread crossed its rolling average (minimum 6) |
| `leg_weight_a` | number | 1 / (1 + β) — A's share of gross exposure |
| `leg_weight_b` | number | β / (1 + β) — B's share of gross exposure (neither leg may exceed 0.80) |
| `formation_start` / `formation_end` | string | First 60% of common dates (fits the line) |
| `evaluation_start` / `evaluation_end` | string | Final 40% (out-of-sample simulation only) |

### `SignalStats`

| Field | Type | Meaning |
| --- | --- | --- |
| `current_spread` | number | log A − intercept − β·log B on the latest evaluation date, using the **frozen** formation fit |
| `rolling_mean` | number | Average of the previous 60 spreads, excluding today |
| `rolling_std` | number | Standard deviation of those previous 60 spreads |
| `z_score` | number | (current spread − rolling mean) / rolling std |
| `as_of_date` | string | Latest evaluation date — the signal date |
| `entry_z` / `exit_z` / `stop_z` | number | 2.0 / 0.5 / 3.5 (frozen thresholds, echoed for display) |
| `max_holding_days` | int | 20 (frozen) |

### `TradeRecord` (one row of the shared trade ledger)

| Field | Type | Meaning |
| --- | --- | --- |
| `signal_date` | string | Close on which the entry decision was formed |
| `entry_date` | string | **Next** trading day — executed at that day's open |
| `exit_signal_date` | string \| null | Close on which the exit decision was formed |
| `exit_date` | string \| null | Next trading day's open where the exit executed |
| `direction` | `"SELL_A_BUY_B"` \| `"BUY_A_SELL_B"` | In displayed A/B order |
| `entry_beta` | number | Frozen formation beta at entry |
| `qty_a` / `qty_b` | number | Signed unit quantities per 1.0 gross exposure, frozen from entry until exit |
| `entry_price_a` / `entry_price_b` | number | Adjusted open prices at entry |
| `exit_price_a` / `exit_price_b` | number \| null | Adjusted open prices at exit |
| `costs` | number | Total costs as a fraction of gross exposure — `cost_bps` × \|traded notional\| charged **separately on both legs at entry and both legs at exit** (four cost events) |
| `exit_reason` | `ExitReason` \| null | Why the trade closed (below) |
| `holding_days` | int \| null | Trading days held (forced exit at 20) |
| `pnl` | number \| null | After-cost profit/loss as a fraction of gross exposure |

**`ExitReason`**

| Value | Meaning |
| --- | --- |
| `target` | \|z\| fell to the 0.5 exit threshold |
| `stop` | \|z\| reached the 3.5 stop threshold |
| `time` | Maximum holding period of 20 trading days reached |
| `end_of_sample` | Sample ended with the trade still open; closed at the final prices |

### `BacktestMetrics`

Simulated only on the final 40% evaluation period the fit never saw, with the
formation correlation/intercept/beta frozen, at most one open position, and
short proceeds treated as collateral (not reusable cash).

| Field | Type | Meaning |
| --- | --- | --- |
| `n_trades` | int | Completed trades |
| `net_profit` | number | After-cost profit, fraction of gross exposure |
| `net_return` | number | Compounded after-cost evaluation-period return |
| `gross_return` | number | Same, before costs |
| `win_rate` | number \| null | Fraction of winning trades |
| `avg_win` / `avg_loss` | number \| null | Average winning / losing trade |
| `profit_factor` | number \| null | Gross wins ÷ \|gross losses\| (gate: > 1.0) |
| `max_drawdown` | number | Worst equity peak-to-trough (gate: ≥ −0.20) |
| `avg_holding_days` | number \| null | Mean holding period |
| `total_costs` | number | Total estimated transaction costs |
| `screen_passed` | bool | All four gate conditions true: ≥ 5 trades, net profit > 0, profit factor > 1.0, drawdown ≥ −20% |
| `limited_evidence` | bool | `true` when 5–9 completed trades — never call five trades statistically reliable |
| `worst_trade_pnl` | number \| null | Worst single-trade loss (drives the stress estimate) |

Passing the screen is a **product decision, not proof that future profit
exists**.

### `SizingResult`

| Field | Type | Meaning |
| --- | --- | --- |
| `sized` | bool | Whether a feasible size was found |
| `reason` | string \| null | Plain-English reason when `sized` is `false` |
| `legs` | `SizingLeg[]` | The two legs: `ticker`, `side` (`BUY`/`SELL`), `shares`, `price`, `notional` |
| `gross_exposure` | number | Sum of absolute leg notionals |
| `net_exposure` | number | Signed sum of leg notionals |
| `estimated_cost` | number | `cost_bps` × gross, on both legs at entry **and** exit (all four legs) |
| `stress_loss_estimate` | number | Worst historical trade % loss × proposed gross (fallback 3% of gross when no losing trade exists) — not a guaranteed maximum loss |
| `risk_budget` | number | Profile stress-loss allowance in currency |
| `max_gross_allowed` | number | Profile gross-exposure cap in currency |
| `remaining_cash` | number | Unallocated cash; short-sale proceeds are collateral, never extra spending money |

Target notionals: A gets G/(1+β), B gets βG/(1+β) where G is the allowed
gross. Whole-share mode searches a small bounded area (radius 3) around the
rounded quantities for the feasible pair closest to the target ratio;
fractional mode rounds to 4 decimal places. Legs are scaled down
proportionally until the stress estimate fits the profile's loss budget; if
the minimum feasible whole-share pair still breaks the limit, `sized` is
`false` with an explanation.

### `EvidenceCard`

| Field | Type | Meaning |
| --- | --- | --- |
| `key` | enum | `move_together`, `stable_relationship`, `unusual_today`, `worked_historically` |
| `title` | string | Display title |
| `status` | `CardStatus` | `pass`, `caution` or `fail` |
| `headline_value` | string | e.g. `"0.74"` or `"z = +2.31"` |
| `detail_lines` | string[] | Values and thresholds shown on the card |
| `how_this_works` | string | One–two sentence tooltip |
| `plain_english` | string | Plain-English takeaway |

Convention: `worked_historically` shows `caution` when the screen passed with
only 5–9 trades (limited evidence).

### `Charts`

| Field | Contents |
| --- | --- |
| `normalised_prices` | `a`, `b`: `SeriesPoint[]` — both stocks set to 100 on the first common date |
| `spread` | `spread`, `rolling_mean`, `upper_entry`/`lower_entry` (mean ± 2σ), `upper_stop`/`lower_stop` (mean ± 3.5σ): `SeriesPoint[]`; `markers`: `SpreadMarker[]` (historical entries/exits with `date`, `kind`, `direction`, `z`); `formation_end`: the formation/evaluation boundary date |
| `equity` | `equity`: `SeriesPoint[]` — after-cost equity, starts at 1.0 |

`SeriesPoint` is `{ "date": "YYYY-MM-DD", "value": number | null }` (null for
warm-up dates without a rolling value). Charts are rendered directly from
these series; the frontend computes nothing.

---

## POST /api/narrative

Called independently after `/api/analyse` when the Narrative Lens is on. The
quant request's direction, z-score, trade result and sizing are **not** sent
to the model — the news classification is independent, not anchored to the
proposed trade. Identical requests are cached for one hour.

### Request — `NarrativeRequest`

| Field | Type | Default | Validation | Meaning |
| --- | --- | --- | --- | --- |
| `ticker_a` | string | — (required) | 1–12 chars | Displayed stock A |
| `ticker_b` | string | — (required) | 1–12 chars | Displayed stock B |
| `data_mode` | enum | `"live"` | `live` \| `fixture` | Live news + DeepSeek, or recorded fixture |

### Response — `NarrativeResponse`

| Field | Type | Meaning |
| --- | --- | --- |
| `ai_status` | `AiStatus` | Delivery status of the AI layer (below) |
| `model` | string \| null | Model name used (or preserved from the recording) |
| `classification` | `NarrativeClassification` | The structured verdict (below) |
| `confidence` | `LOW` \| `MEDIUM` \| `HIGH` \| null | Model's stated confidence — **never** a probability of profit |
| `summary_a` / `summary_b` | string \| null | One sentence per company |
| `shared_story` | string \| null | One sentence if a shared macro/sector story exists |
| `risk_flags` | string[] | Short risk strings |
| `evidence` | `EvidenceClaim[]` | Up to 3 claims, each `{ claim, source_ids }`; claims citing source IDs that were not supplied are **rejected server-side** |
| `explanation` | string \| null | Plain English, at most 70 words |
| `news_items` | `NewsItem[]` | The exact items supplied to the model, so every citation can be rendered beside its source |
| `elevated_news_risk` | bool | `true` when classification is `POSSIBLE_COMPANY_SPECIFIC_EXPLANATION` — the UI shows a prominent **Elevated news risk** warning beside the quant setup |
| `recorded_at` | string \| null | Set when `ai_status` is `recorded` |

**`AiStatus` — every value**

| Value | Meaning |
| --- | --- |
| `ok` | Live DeepSeek call succeeded and its JSON validated against the schema |
| `unavailable` | DeepSeek is configured but the call failed (timeout after one retry, transport error, or invalid JSON) — the quant analysis remains fully usable |
| `not_configured` | No `DEEPSEEK_API_KEY` set server-side |
| `insufficient_news` | Fewer than 2 usable items in the last 30 days for at least one company — no model call is made |
| `recorded` | A frozen fixture DeepSeek response was replayed for the offline demo; the UI labels it **Recorded AI response**, never live AI, and `recorded_at` + the recorded `model` are preserved |

**`NarrativeClassification` — every value**

| Value | Meaning |
| --- | --- |
| `NO_OBVIOUS_NEWS_EXPLANATION` | The supplied headlines reveal no obvious company-specific explanation for the gap — this does **not** mean a trade will profit |
| `POSSIBLE_COMPANY_SPECIFIC_EXPLANATION` | Recent news could make the price gap less likely to revert — treated as elevated news risk |
| `MIXED` | The supplied items point in conflicting directions |
| `INSUFFICIENT_NEWS` | A relevant company had fewer than two usable recent items |
| `AI_UNAVAILABLE` | No model output is available (pairs with `ai_status` of `unavailable` or `not_configured`) |

**`NewsItem`**

| Field | Type | Meaning |
| --- | --- | --- |
| `source_id` | string | Stable provider ID — the only IDs the model may cite |
| `ticker` | string | Which company the item is about |
| `headline` | string | Headline text (treated as untrusted quoted data) |
| `snippet` | string \| null | Short snippet, may be missing |
| `source` | string | Publisher name |
| `published_at` | string | ISO-8601 publication time (last 30 days only) |
| `url` | string \| null | Canonicalised link |

Grounding guarantees: the model receives only ticker, company name, headline,
snippet, source, date and source ID as delimited structured JSON; it is
instructed to use no outside knowledge, invent nothing, treat news text as
untrusted data, and return JSON only. Output is validated with Pydantic and
evidence citing unknown source IDs is stripped before the response is
returned. The classification never changes the backtest, direction or share
quantities. Latency and status are logged; the API key and full prompts are
not.

---

## Error envelope — `ApiError`

All structured errors use this shape; raw stack traces are never returned.

| Field | Type | Meaning |
| --- | --- | --- |
| `error` | string | Machine-readable code (e.g. `"provider_error"`, `"validation_error"`) |
| `message` | string | Human-readable, plain English |
| `details` | object \| null | Optional structured context |

```json
{
  "error": "validation_error",
  "message": "cost_bps must be between 0 and 200 basis points.",
  "details": { "field": "cost_bps" }
}
```

---

## Complete example

From `docs/example_api_response.json` (a schema-validated contract example
for the KO/PEP fixture pair; values are illustrative).

### Request

```json
POST /api/analyse
{
  "ticker_a": "KO",
  "ticker_b": "PEP",
  "starting_capital": 10000.0,
  "risk_profile": "balanced",
  "lookback": "2y",
  "whole_shares": true,
  "cost_bps": 10.0,
  "data_mode": "fixture"
}
```

### Response (abbreviated chart arrays — full version in `docs/example_api_response.json`)

```json
{
  "request": {
    "ticker_a": "KO", "ticker_b": "PEP", "starting_capital": 10000.0,
    "risk_profile": "balanced", "lookback": "2y", "whole_shares": true,
    "cost_bps": 10.0, "data_mode": "fixture"
  },
  "data": {
    "provider": "fixture", "retrieved_at": "2026-07-13T12:00:00+00:00",
    "last_market_date": "2026-07-13", "currency": "USD",
    "n_common_observations": 502, "is_fixture": true,
    "fixture_captured_at": "2026-07-13T12:00:00+00:00",
    "exchange_a": "NYQ", "exchange_b": "NMS"
  },
  "state": "SELL_A_BUY_B",
  "explanation": "KO looks unusually expensive relative to PEP (z = +2.31), and the fixed rule passed the minimum historical screen after costs.",
  "relationship": {
    "correlation": 0.74, "beta": 0.86, "intercept": 1.21,
    "split_beta_change": 0.18, "mean_crossings": 14,
    "leg_weight_a": 0.5376, "leg_weight_b": 0.4624,
    "formation_start": "2024-07-15", "formation_end": "2025-09-26",
    "evaluation_start": "2025-09-29", "evaluation_end": "2026-07-13"
  },
  "signal": {
    "current_spread": 0.0342, "rolling_mean": 0.0021, "rolling_std": 0.0139,
    "z_score": 2.31, "as_of_date": "2026-07-13",
    "entry_z": 2.0, "exit_z": 0.5, "stop_z": 3.5, "max_holding_days": 20
  },
  "backtest": {
    "n_trades": 7, "net_profit": 0.043, "net_return": 0.043,
    "gross_return": 0.058, "win_rate": 0.714, "avg_win": 0.011,
    "avg_loss": -0.006, "profit_factor": 2.4, "max_drawdown": -0.031,
    "avg_holding_days": 8.3, "total_costs": 0.0056,
    "screen_passed": true, "limited_evidence": true, "worst_trade_pnl": -0.009
  },
  "trades": [
    {
      "signal_date": "2025-11-03", "entry_date": "2025-11-04",
      "exit_signal_date": "2025-11-12", "exit_date": "2025-11-13",
      "direction": "SELL_A_BUY_B", "entry_beta": 0.86,
      "qty_a": -0.0089, "qty_b": 0.0031,
      "entry_price_a": 60.12, "entry_price_b": 148.3,
      "exit_price_a": 58.9, "exit_price_b": 149.1,
      "costs": 0.0004, "exit_reason": "target", "holding_days": 7, "pnl": 0.0121
    }
  ],
  "sizing": {
    "sized": true, "reason": null,
    "legs": [
      { "ticker": "KO", "side": "SELL", "shares": 67.0, "price": 60.12, "notional": 4028.04 },
      { "ticker": "PEP", "side": "BUY", "shares": 23.0, "price": 148.3, "notional": 3410.9 }
    ],
    "gross_exposure": 7438.94, "net_exposure": -617.14,
    "estimated_cost": 14.88, "stress_loss_estimate": 66.95,
    "risk_budget": 100.0, "max_gross_allowed": 7500.0, "remaining_cash": 6589.1
  },
  "evidence_cards": [
    {
      "key": "move_together", "title": "Move together", "status": "pass",
      "headline_value": "0.74",
      "detail_lines": ["Return correlation: 0.74", "Threshold: at least 0.60"],
      "how_this_works": "We measure how strongly the two stocks' daily percentage moves line up. 1.0 means perfectly together, 0 means unrelated.",
      "plain_english": "Their daily moves lined up strongly."
    },
    {
      "key": "stable_relationship", "title": "Stable enough relationship", "status": "pass",
      "headline_value": "beta 0.86",
      "detail_lines": ["Beta: 0.86", "Beta change between halves: 18%", "Spread crossings: 14", "Largest leg: 54%"],
      "how_this_works": "A line of best fit describes their normal price relationship. We check the ratio did not change dramatically.",
      "plain_english": "The line-of-best-fit relationship is usable."
    },
    {
      "key": "unusual_today", "title": "Unusual today", "status": "pass",
      "headline_value": "z = +2.31",
      "detail_lines": ["Current z-score: +2.31", "Entry threshold: 2.0"],
      "how_this_works": "The z-score counts how many recent standard deviations today's gap is from normal.",
      "plain_english": "Today's gap is large enough to act on."
    },
    {
      "key": "worked_historically", "title": "Worked historically", "status": "caution",
      "headline_value": "7 trades, +4.3%",
      "detail_lines": ["Completed trades: 7 (limited evidence)", "Net profit after costs: +4.3%", "Profit factor: 2.4", "Max drawdown: -3.1%"],
      "how_this_works": "We replay the unchanged rule on later dates the fit never saw, entering at the next day's open and subtracting costs.",
      "plain_english": "The fixed rule cleared the minimum historical screen after costs, but 7 trades is limited evidence."
    }
  ],
  "charts": {
    "normalised_prices": { "a": ["…SeriesPoint…"], "b": ["…SeriesPoint…"] },
    "spread": {
      "spread": ["…"], "rolling_mean": ["…"],
      "upper_entry": ["…"], "lower_entry": ["…"],
      "upper_stop": ["…"], "lower_stop": ["…"],
      "markers": [
        { "date": "2025-11-03", "kind": "entry", "direction": "SELL_A_BUY_B", "z": 2.14 },
        { "date": "2025-11-12", "kind": "exit", "direction": "SELL_A_BUY_B", "z": 0.42 }
      ],
      "formation_end": "2025-09-26"
    },
    "equity": { "equity": ["…"] }
  },
  "warnings": [
    "Historical performance does not guarantee future results.",
    "Recorded market snapshot — fixture data captured 2026-07-13."
  ],
  "methodology_version": "1.0.0"
}
```

### Narrative request/response

```json
POST /api/narrative
{ "ticker_a": "KO", "ticker_b": "PEP", "data_mode": "fixture" }
```

```json
{
  "ai_status": "ok",
  "model": "deepseek-v4-flash",
  "classification": "NO_OBVIOUS_NEWS_EXPLANATION",
  "confidence": "MEDIUM",
  "summary_a": "Coca-Cola's recent coverage centres on routine earnings previews and dividend commentary.",
  "summary_b": "PepsiCo's headlines discuss snack-division marketing and an analyst rating maintenance.",
  "shared_story": null,
  "risk_flags": ["Routine earnings coverage for both companies"],
  "evidence": [
    {
      "claim": "Coverage of both companies is routine rather than event-driven.",
      "source_ids": ["yf-a1", "yf-b2"]
    }
  ],
  "explanation": "The supplied headlines show routine coverage for both companies and no obvious company-specific event that would explain the current price gap.",
  "news_items": [
    {
      "source_id": "yf-a1", "ticker": "KO",
      "headline": "Example headline about KO", "snippet": "Short snippet.",
      "source": "Reuters", "published_at": "2026-07-09T14:00:00+00:00",
      "url": "https://example.com/a1"
    },
    {
      "source_id": "yf-b2", "ticker": "PEP",
      "headline": "Example headline about PEP", "snippet": "Short snippet.",
      "source": "Bloomberg", "published_at": "2026-07-08T09:00:00+00:00",
      "url": "https://example.com/b2"
    }
  ],
  "elevated_news_risk": false,
  "recorded_at": null
}
```

---

## Warnings that accompany every analysis

- Historical performance does not guarantee future results.
- Correlation and price relationships can break.
- yfinance is an unofficial data source and can be delayed or incomplete.
- Costs are estimated; bid-ask spreads, borrow availability and fees,
  dividends on short positions, market impact, taxes and corporate events are
  not fully modelled.
- Proposed trades are paper examples only, not financial advice.
- AI summaries can be incomplete or wrong and must be checked against their
  linked sources.
