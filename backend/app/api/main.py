"""PairScope FastAPI application.

Decision-state ownership (docs/INTERFACES.md): this layer decides
PROVIDER_ERROR, INSUFFICIENT_DATA and the identical-ticker /
currency-mismatch UNSUITABLE_PAIR cases BEFORE the quant engine runs.
The quant engine (Agent A) owns every other state and is reached through
a lazy import seam so this module never imports it at module load time.

POST /api/analyse never waits for DeepSeek; the frontend calls
POST /api/narrative independently. Every error path returns structured
ApiError JSON — never a raw stack trace.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env BEFORE importing config so env-driven settings
# (DeepSeek key, CORS) are present when config reads the environment.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import logging  # noqa: E402
from collections.abc import Callable  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Annotated  # noqa: E402

import yfinance  # noqa: E402
from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app import config  # noqa: E402
from app.ai import lens  # noqa: E402
from app.ai.deepseek import (  # noqa: E402
    DeepSeekNarrativeProvider,
    NarrativeProvider,
    RecordedNarrativeProvider,
)
from app.data.cleaning import (  # noqa: E402
    align_pair,
    clean_price_frame,
    is_stale,
    min_required_observations,
)
from app.data.fixture_provider import (  # noqa: E402
    DEFAULT_FIXTURES_DIR,
    FixtureNewsProvider,
    FixturePriceProvider,
)
from app.data.provider import (  # noqa: E402
    NewsProvider,
    PriceProvider,
    ProviderError,
    parse_published_at,
)
from app.data.yfinance_provider import (  # noqa: E402
    YFinanceNewsProvider,
    YFinancePriceProvider,
)
from app.schemas import (  # noqa: E402
    AiStatus,
    AnalyseRequest,
    AnalyseResponse,
    ApiError,
    DataMetadata,
    DataMode,
    FinalState,
    HealthResponse,
    NarrativeClassification,
    NarrativeRequest,
    NarrativeResponse,
    QuantResult,
    SymbolSearchResponse,
    SymbolSearchResult,
)

logger = logging.getLogger("pairscope.api")

# Standard warnings (spec section 14) attached to every analysis response.
STANDARD_WARNINGS = [
    "Historical performance does not guarantee future results.",
    "Correlation and price relationships can break.",
    "yfinance is an unofficial data source and can be delayed or incomplete.",
    (
        "The model estimates costs but does not fully model bid-ask spreads, "
        "borrow availability, borrow fees, dividends on short positions, "
        "market impact, taxes or corporate events."
    ),
    "Proposed trades are paper examples only, not financial advice.",
    (
        "AI summaries can be incomplete or wrong and must be checked against "
        "their linked sources."
    ),
]

app = FastAPI(
    title="PairScope API",
    version=config.METHODOLOGY_VERSION,
    description="Transparent hybrid stat-arb research tool (educational use only).",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dependency seams (overridable in tests)
# ---------------------------------------------------------------------------

_live_price_provider = YFinancePriceProvider()
_fixture_price_provider = FixturePriceProvider()
_live_news_provider = YFinanceNewsProvider()
_fixture_news_provider = FixtureNewsProvider()


def get_price_provider_factory() -> Callable[[DataMode], PriceProvider]:
    def factory(mode: DataMode) -> PriceProvider:
        return _fixture_price_provider if mode == DataMode.FIXTURE else _live_price_provider

    return factory


def get_news_provider_factory() -> Callable[[DataMode], NewsProvider]:
    def factory(mode: DataMode) -> NewsProvider:
        return _fixture_news_provider if mode == DataMode.FIXTURE else _live_news_provider

    return factory


def get_run_analysis():
    """Lazy import seam for the quant engine (built concurrently by Agent A).

    Exposed as a FastAPI dependency so tests override it with a fake that
    returns a canned app.schemas.QuantResult.
    """
    from app.quant.engine import run_analysis

    return run_analysis


def get_narrative_selector() -> Callable[[NarrativeRequest], NarrativeProvider | None]:
    """Choose the narrative provider for a request; None means not configured.

    Fixture mode replays a recorded DeepSeek response when one exists for
    the pair (labelled "recorded", never live AI); otherwise the live
    provider is used when a key is configured.
    """

    def select(request: NarrativeRequest) -> NarrativeProvider | None:
        if request.data_mode == DataMode.FIXTURE:
            recorded = RecordedNarrativeProvider.find(
                DEFAULT_FIXTURES_DIR, request.ticker_a, request.ticker_b
            )
            if recorded is not None:
                return recorded
        if config.DEEPSEEK_API_KEY:
            return DeepSeekNarrativeProvider()
        return None

    return select


# ---------------------------------------------------------------------------
# Error handlers — structured ApiError JSON, never raw stack traces
# ---------------------------------------------------------------------------


@app.exception_handler(ProviderError)
async def provider_error_handler(request, exc: ProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=ApiError(error="PROVIDER_ERROR", message=str(exc)).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"loc": [str(part) for part in e.get("loc", [])], "msg": str(e.get("msg", ""))}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ApiError(
            error="VALIDATION_ERROR",
            message="The request was invalid; check the listed fields.",
            details={"errors": errors},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ApiError(
            error="INTERNAL_ERROR",
            message="An unexpected server error occurred. Please try again.",
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Simple endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=config.METHODOLOGY_VERSION,
        deepseek_configured=bool(config.DEEPSEEK_API_KEY),
    )


@app.get("/api/methodology")
def methodology() -> dict:
    return config.methodology()


@app.get("/api/symbols/search", response_model=SymbolSearchResponse)
def symbols_search(q: str = "") -> SymbolSearchResponse:
    """Best-effort symbol autocomplete; returns empty results on any failure.

    Direct ticker entry always works regardless of this endpoint.
    """
    query = q.strip()
    if not query:
        return SymbolSearchResponse(results=[])
    try:
        quotes = yfinance.Search(query, max_results=8, news_count=0).quotes or []
    except Exception as exc:
        logger.info("symbol search failed for %r: %r", query, exc)
        return SymbolSearchResponse(results=[])
    results = []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        results.append(
            SymbolSearchResult(
                symbol=symbol,
                name=quote.get("shortname") or quote.get("longname") or symbol,
                exchange=quote.get("exchDisp") or quote.get("exchange"),
                currency=quote.get("currency"),
            )
        )
    return SymbolSearchResponse(results=results)


# ---------------------------------------------------------------------------
# POST /api/analyse
# ---------------------------------------------------------------------------


def _fixture_banner(fixture_captured_at: str | None) -> str:
    captured = (fixture_captured_at or "")[:10] or "unknown date"
    return f"Recorded market snapshot — fixture data captured {captured}"


def _finish(
    request: AnalyseRequest,
    state: FinalState,
    explanation: str,
    *,
    data: DataMetadata | None = None,
    warnings: list[str] | None = None,
    quant: QuantResult | None = None,
) -> AnalyseResponse:
    """Assemble the response with a deterministic warning order:
    data warnings, quant warnings, fixture banner, standard warnings."""
    all_warnings = list(warnings or [])
    if quant is not None:
        all_warnings.extend(quant.warnings)
    if data is not None and data.is_fixture:
        all_warnings.append(_fixture_banner(data.fixture_captured_at))
    all_warnings.extend(STANDARD_WARNINGS)
    return AnalyseResponse(
        request=request,
        data=data,
        state=state,
        explanation=explanation,
        relationship=quant.relationship if quant else None,
        signal=quant.signal if quant else None,
        backtest=quant.backtest if quant else None,
        trades=quant.trades if quant else [],
        sizing=quant.sizing if quant else None,
        evidence_cards=quant.evidence_cards if quant else [],
        charts=quant.charts if quant else None,
        warnings=all_warnings,
        methodology_version=config.METHODOLOGY_VERSION,
    )


def _later_iso(first: str | None, second: str | None) -> str | None:
    """Pick the later of two ISO timestamps, keeping the original string."""
    if first is None:
        return second
    if second is None:
        return first
    dt_first, dt_second = parse_published_at(first), parse_published_at(second)
    if dt_first is None or dt_second is None:
        return max(first, second)
    return first if dt_first >= dt_second else second


@app.post("/api/analyse", response_model=AnalyseResponse)
def analyse(
    request: AnalyseRequest,
    price_factory: Annotated[
        Callable[[DataMode], PriceProvider], Depends(get_price_provider_factory)
    ],
    run_quant: Annotated[Callable[..., QuantResult], Depends(get_run_analysis)],
) -> AnalyseResponse:
    ticker_a = request.ticker_a.strip().upper()
    ticker_b = request.ticker_b.strip().upper()

    # 1. Identical tickers (case-insensitive) — no data fetch needed.
    if ticker_a == ticker_b:
        return _finish(
            request,
            FinalState.UNSUITABLE_PAIR,
            f"'{ticker_a}' and '{ticker_b}' are the same stock; a pair needs two "
            "different stocks.",
        )

    # 2. Fetch both histories (fixture or live per data_mode).
    provider = price_factory(request.data_mode)
    try:
        history_a = provider.get_history(ticker_a, request.lookback.value)
        history_b = provider.get_history(ticker_b, request.lookback.value)
    except ProviderError as exc:
        return _finish(request, FinalState.PROVIDER_ERROR, str(exc))

    # 3. Currency mismatch.
    if history_a.currency != history_b.currency:
        return _finish(
            request,
            FinalState.UNSUITABLE_PAIR,
            f"{ticker_a} is quoted in {history_a.currency} but {ticker_b} is quoted "
            f"in {history_b.currency}; PairScope only analyses pairs quoted in the "
            "same currency.",
        )

    # 4. Clean and align to common trading dates.
    df_a, df_b = align_pair(clean_price_frame(history_a.df), clean_price_frame(history_b.df))
    n_common = len(df_a)

    metadata = DataMetadata(
        provider=history_a.provider,
        retrieved_at=_later_iso(history_a.retrieved_at, history_b.retrieved_at) or "",
        last_market_date=(
            str(df_a.index[-1].date())
            if n_common
            else min(history_a.last_market_date, history_b.last_market_date)
        ),
        currency=history_a.currency,
        n_common_observations=n_common,
        is_fixture=history_a.is_fixture or history_b.is_fixture,
        fixture_captured_at=_later_iso(
            history_a.fixture_captured_at, history_b.fixture_captured_at
        ),
        exchange_a=history_a.exchange,
        exchange_b=history_b.exchange,
    )

    # 5. Minimum common observations.
    required = min_required_observations(request.lookback.value)
    if n_common < required:
        return _finish(
            request,
            FinalState.INSUFFICIENT_DATA,
            f"Only {n_common} common trading days are available; at least {required} "
            f"are required for a {request.lookback.value} lookback.",
            data=metadata,
        )

    # 6. Staleness and calendar differences are warnings, not errors.
    warnings: list[str] = []
    for symbol, history in ((ticker_a, history_a), (ticker_b, history_b)):
        retrieved = parse_published_at(history.retrieved_at) or datetime.now(UTC)
        if is_stale(history.last_market_date, retrieved):
            warnings.append(
                f"Price data for {symbol} may be stale: its last market date "
                f"{history.last_market_date} is more than {config.STALE_CALENDAR_DAYS} "
                "calendar days before retrieval."
            )
    if history_a.exchange and history_b.exchange and history_a.exchange != history_b.exchange:
        warnings.append(
            f"{ticker_a} and {ticker_b} trade on different exchanges "
            f"({history_a.exchange} vs {history_b.exchange}); their trading "
            "calendars may differ."
        )
    for symbol, history in ((ticker_a, history_a), (ticker_b, history_b)):
        if history.currency_guessed:
            warnings.append(
                f"The data provider did not report a quote currency for {symbol}; "
                "USD was assumed, so the same-currency check could not be fully "
                "verified for this pair."
            )

    # 7. Quant engine (lazy seam). The response never waits for DeepSeek.
    quant = run_quant(
        df_a,
        df_b,
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        starting_capital=request.starting_capital,
        risk_profile=request.risk_profile.value,
        whole_shares=request.whole_shares,
        cost_bps=request.cost_bps,
    )
    return _finish(
        request, quant.state, quant.explanation, data=metadata, warnings=warnings, quant=quant
    )


# ---------------------------------------------------------------------------
# POST /api/narrative — independent of /api/analyse
# ---------------------------------------------------------------------------


@app.post("/api/narrative", response_model=NarrativeResponse)
def narrative(
    request: NarrativeRequest,
    news_factory: Annotated[
        Callable[[DataMode], NewsProvider], Depends(get_news_provider_factory)
    ],
    select_provider: Annotated[
        Callable[[NarrativeRequest], NarrativeProvider | None],
        Depends(get_narrative_selector),
    ],
) -> NarrativeResponse:
    ticker_a = request.ticker_a.strip().upper()
    ticker_b = request.ticker_b.strip().upper()

    try:
        news_provider = news_factory(request.data_mode)
        items_a = news_provider.get_news(ticker_a)
        items_b = news_provider.get_news(ticker_b)
    except ProviderError as exc:
        logger.info("narrative news fetch failed: %s", exc)
        return NarrativeResponse(
            ai_status=AiStatus.UNAVAILABLE,
            classification=NarrativeClassification.AI_UNAVAILABLE,
            explanation=f"News could not be fetched: {exc} The quant analysis is unaffected.",
        )

    provider = select_provider(request)
    if provider is None:
        return NarrativeResponse(
            ai_status=AiStatus.NOT_CONFIGURED,
            classification=NarrativeClassification.AI_UNAVAILABLE,
            news_items=lens.prepare_items(items_a) + lens.prepare_items(items_b),
            explanation=(
                "The Narrative Lens is not configured; set DEEPSEEK_API_KEY to "
                "enable AI news context. The quant analysis is unaffected."
            ),
        )
    return lens.run_narrative(ticker_a, ticker_b, items_a, items_b, provider)
