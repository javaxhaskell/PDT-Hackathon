"""Frozen Pydantic contracts for the PairScope API.

These schemas are the boundary between the quant engine, the API and the
frontend. Contract mismatches are resolved here, never with frontend
workarounds. Only the orchestrator may change this file.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class Lookback(str, Enum):
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    THREE_YEARS = "3y"


class DataMode(str, Enum):
    LIVE = "live"
    FIXTURE = "fixture"


class FinalState(str, Enum):
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNSUITABLE_PAIR = "UNSUITABLE_PAIR"
    HISTORICAL_SCREEN_FAILED = "HISTORICAL_SCREEN_FAILED"
    WAIT = "WAIT"
    BUY_A_SELL_B = "BUY_A_SELL_B"
    SELL_A_BUY_B = "SELL_A_BUY_B"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class CardStatus(str, Enum):
    PASS = "pass"
    CAUTION = "caution"
    FAIL = "fail"


class NarrativeClassification(str, Enum):
    NO_OBVIOUS_NEWS_EXPLANATION = "NO_OBVIOUS_NEWS_EXPLANATION"
    POSSIBLE_COMPANY_SPECIFIC_EXPLANATION = "POSSIBLE_COMPANY_SPECIFIC_EXPLANATION"
    MIXED = "MIXED"
    INSUFFICIENT_NEWS = "INSUFFICIENT_NEWS"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"


class NarrativeConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AiStatus(str, Enum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"
    INSUFFICIENT_NEWS = "insufficient_news"
    RECORDED = "recorded"  # replayed fixture response, not live AI


class ExitReason(str, Enum):
    TARGET = "target"          # |z| fell to exit threshold
    STOP = "stop"              # |z| reached stop threshold
    TIME = "time"              # max holding days reached
    END_OF_SAMPLE = "end_of_sample"


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class AnalyseRequest(BaseModel):
    ticker_a: str = Field(min_length=1, max_length=12)
    ticker_b: str = Field(min_length=1, max_length=12)
    starting_capital: float = Field(default=10_000.0, gt=0)
    risk_profile: RiskProfile = RiskProfile.BALANCED
    lookback: Lookback = Lookback.TWO_YEARS
    whole_shares: bool = True
    cost_bps: float = Field(default=10.0, ge=0, le=200)
    data_mode: DataMode = DataMode.LIVE


class NarrativeRequest(BaseModel):
    ticker_a: str = Field(min_length=1, max_length=12)
    ticker_b: str = Field(min_length=1, max_length=12)
    data_mode: DataMode = DataMode.LIVE


# ---------------------------------------------------------------------------
# Data metadata
# ---------------------------------------------------------------------------


class DataMetadata(BaseModel):
    provider: str                              # "yfinance" or "fixture"
    retrieved_at: str                          # ISO-8601 UTC
    last_market_date: str                      # YYYY-MM-DD
    currency: str
    n_common_observations: int
    is_fixture: bool
    fixture_captured_at: Optional[str] = None  # ISO-8601, fixture mode only
    exchange_a: Optional[str] = None
    exchange_b: Optional[str] = None


# ---------------------------------------------------------------------------
# Quant blocks
# ---------------------------------------------------------------------------


class RelationshipStats(BaseModel):
    correlation: float
    beta: float
    intercept: float
    split_beta_change: float        # |beta_h1 - beta_h2| / |beta_full|
    mean_crossings: int
    leg_weight_a: float             # 1 / (1 + beta)
    leg_weight_b: float             # beta / (1 + beta)
    formation_start: str
    formation_end: str
    evaluation_start: str
    evaluation_end: str


class SignalStats(BaseModel):
    current_spread: float
    rolling_mean: float
    rolling_std: float
    z_score: float
    as_of_date: str                 # latest evaluation date (signal date)
    entry_z: float
    exit_z: float
    stop_z: float
    max_holding_days: int


class TradeRecord(BaseModel):
    signal_date: str
    entry_date: str                 # execution at this day's open
    exit_signal_date: Optional[str] = None
    exit_date: Optional[str] = None
    direction: Literal["SELL_A_BUY_B", "BUY_A_SELL_B"]
    entry_beta: float
    qty_a: float                    # signed units of notional (per 1 gross)
    qty_b: float
    entry_price_a: float
    entry_price_b: float
    exit_price_a: Optional[float] = None
    exit_price_b: Optional[float] = None
    costs: float                    # total costs, fraction of gross exposure
    exit_reason: Optional[ExitReason] = None
    holding_days: Optional[int] = None
    pnl: Optional[float] = None     # after-cost, fraction of gross exposure


class BacktestMetrics(BaseModel):
    n_trades: int
    net_profit: float               # after costs, fraction of gross exposure
    net_return: float               # compounded evaluation-period return
    gross_return: float             # before costs
    win_rate: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown: float
    avg_holding_days: Optional[float] = None
    total_costs: float
    screen_passed: bool
    limited_evidence: bool          # true when 5-9 completed trades
    worst_trade_pnl: Optional[float] = None


class SizingLeg(BaseModel):
    ticker: str
    side: Literal["BUY", "SELL"]
    shares: float
    price: float
    notional: float


class SizingResult(BaseModel):
    sized: bool
    reason: Optional[str] = None    # why no size, when sized is false
    legs: list[SizingLeg] = []
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    estimated_cost: float = 0.0
    stress_loss_estimate: float = 0.0
    risk_budget: float = 0.0
    max_gross_allowed: float = 0.0
    remaining_cash: float = 0.0


class EvidenceCard(BaseModel):
    key: Literal[
        "move_together", "stable_relationship", "unusual_today", "worked_historically"
    ]
    title: str
    status: CardStatus
    headline_value: str             # e.g. "0.82" or "z = +2.31"
    detail_lines: list[str]
    how_this_works: str
    plain_english: str


# ---------------------------------------------------------------------------
# Chart series
# ---------------------------------------------------------------------------


class SeriesPoint(BaseModel):
    date: str
    value: Optional[float] = None


class NormalisedPricesChart(BaseModel):
    a: list[SeriesPoint]
    b: list[SeriesPoint]


class SpreadMarker(BaseModel):
    date: str
    kind: Literal["entry", "exit"]
    direction: Literal["SELL_A_BUY_B", "BUY_A_SELL_B"]
    z: float


class SpreadChart(BaseModel):
    spread: list[SeriesPoint]
    rolling_mean: list[SeriesPoint]
    upper_entry: list[SeriesPoint]     # mean + 2 std
    lower_entry: list[SeriesPoint]     # mean - 2 std
    upper_stop: list[SeriesPoint]      # mean + 3.5 std
    lower_stop: list[SeriesPoint]      # mean - 3.5 std
    markers: list[SpreadMarker]
    formation_end: str                 # boundary between formation/evaluation


class EquityChart(BaseModel):
    equity: list[SeriesPoint]          # after-cost, starts at 1.0


class Charts(BaseModel):
    normalised_prices: NormalisedPricesChart
    spread: SpreadChart
    equity: EquityChart


# ---------------------------------------------------------------------------
# Analyse response
# ---------------------------------------------------------------------------


class AnalyseResponse(BaseModel):
    request: AnalyseRequest
    data: Optional[DataMetadata] = None
    state: FinalState
    explanation: str                    # one sentence, plain English
    relationship: Optional[RelationshipStats] = None
    signal: Optional[SignalStats] = None
    backtest: Optional[BacktestMetrics] = None
    trades: list[TradeRecord] = []
    sizing: Optional[SizingResult] = None
    evidence_cards: list[EvidenceCard] = []
    charts: Optional[Charts] = None
    warnings: list[str] = []
    methodology_version: str


# ---------------------------------------------------------------------------
# Narrative Lens
# ---------------------------------------------------------------------------


class NewsItem(BaseModel):
    source_id: str
    ticker: str
    headline: str
    snippet: Optional[str] = None
    source: str
    published_at: str                   # ISO-8601
    url: Optional[str] = None


class EvidenceClaim(BaseModel):
    claim: str
    source_ids: list[str]


class NarrativeResponse(BaseModel):
    ai_status: AiStatus
    model: Optional[str] = None
    classification: NarrativeClassification
    confidence: Optional[NarrativeConfidence] = None
    summary_a: Optional[str] = None
    summary_b: Optional[str] = None
    shared_story: Optional[str] = None
    risk_flags: list[str] = []
    evidence: list[EvidenceClaim] = []
    explanation: Optional[str] = None
    news_items: list[NewsItem] = []     # the exact items supplied to the model
    elevated_news_risk: bool = False
    recorded_at: Optional[str] = None   # set when ai_status == "recorded"


# ---------------------------------------------------------------------------
# Misc endpoints
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    deepseek_configured: bool


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None
    currency: Optional[str] = None


class SymbolSearchResponse(BaseModel):
    results: list[SymbolSearchResult]


class ApiError(BaseModel):
    error: str                          # machine-readable code
    message: str                        # human-readable, plain English
    details: Optional[dict] = None
