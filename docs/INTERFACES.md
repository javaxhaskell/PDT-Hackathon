# Frozen internal interfaces (orchestrator-owned)

These interfaces are the boundary between workstreams. Change requests go to
the orchestrator; agents must not redefine them.

## Quant engine (implemented by Agent A, called by Agent B)

```python
# backend/app/quant/engine.py
def run_analysis(
    df_a: "pd.DataFrame",   # cleaned + aligned by the data layer; ascending
    df_b: "pd.DataFrame",   # DatetimeIndex, identical for both; columns:
                            # "open", "close" — daily ADJUSTED prices
    *,
    ticker_a: str,          # the user's displayed ticker A
    ticker_b: str,          # the user's displayed ticker B
    starting_capital: float,
    risk_profile: str,      # "conservative" | "balanced" | "aggressive"
    whole_shares: bool,
    cost_bps: float,        # per leg per transaction
) -> QuantResult
```

`QuantResult` (Pydantic model in `backend/app/quant/engine.py`) fields:

- `state: FinalState` — one of UNSUITABLE_PAIR, HISTORICAL_SCREEN_FAILED,
  WAIT, BUY_A_SELL_B, SELL_A_BUY_B (data-level states are decided upstream)
- `explanation: str` — one plain-English sentence
- `relationship: RelationshipStats`
- `signal: SignalStats | None` (None only if evaluation window too short)
- `backtest: BacktestMetrics | None`
- `trades: list[TradeRecord]`
- `sizing: SizingResult | None`
- `evidence_cards: list[EvidenceCard]` (always all four when stats exist)
- `charts: Charts | None`
- `warnings: list[str]`

All value types come from `app.schemas`. **Canonicalisation is the engine's
job**: it internally sorts the two tickers alphabetically before fitting,
then maps every output (directions, signs, legs, cards, charts) back to the
user's displayed A/B order. Callers pass displayed order and receive
displayed-order results.

## Data layer (implemented by Agent B, consumed by the API layer)

```python
# backend/app/data/provider.py
class PriceHistory:   # returned per ticker
    df: pd.DataFrame          # DatetimeIndex asc, columns open/close (adjusted)
    currency: str
    exchange: str | None
    last_market_date: str     # YYYY-MM-DD
    provider: str             # "yfinance" | "fixture"
    retrieved_at: str         # ISO-8601 UTC
    is_fixture: bool
    fixture_captured_at: str | None

class PriceProvider(Protocol):
    def get_history(self, ticker: str, lookback: str) -> PriceHistory: ...

class NewsProvider(Protocol):
    def get_news(self, ticker: str) -> list[NewsItem]: ...   # app.schemas.NewsItem
```

Data-level decision states (INSUFFICIENT_DATA, UNSUITABLE_PAIR for identical
tickers / currency mismatch, PROVIDER_ERROR) are produced by the API layer
before the quant engine is invoked. The engine is only called with valid,
aligned data.

## Decision-state ownership

1. PROVIDER_ERROR, INSUFFICIENT_DATA, identical-ticker / currency-mismatch
   UNSUITABLE_PAIR → API/data layer (Agent B).
2. Correlation / beta / crossings / leg-weight UNSUITABLE_PAIR,
   HISTORICAL_SCREEN_FAILED, WAIT, BUY_A_SELL_B, SELL_A_BUY_B → quant engine
   (Agent A).

## File ownership

- Agent A: `backend/app/quant/**`, `backend/tests/quant/**`, `docs/MODEL.md`
- Agent B: `backend/app/{data,ai,api}/**`, `backend/tests/api_data/**`
- Agent C: `frontend/**`
- Agent D: `docs/API.md`, `docs/PRESENTATION.md`, `docs/REVIEW_CHECKLIST.md`
- Orchestrator only: `backend/app/config.py`, `backend/app/schemas/**`,
  root manifests, `Makefile`, `.env.example`, this file.
