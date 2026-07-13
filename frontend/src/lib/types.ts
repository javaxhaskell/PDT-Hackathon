/**
 * TypeScript mirrors of the frozen Pydantic contracts in
 * backend/app/schemas/contracts.py. The backend is the single source of
 * truth for all quant logic; the frontend only renders these values.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type RiskProfile = "conservative" | "balanced" | "aggressive";

export type Lookback = "1y" | "2y" | "3y";

export type DataMode = "live" | "fixture";

export type FinalState =
  | "INSUFFICIENT_DATA"
  | "UNSUITABLE_PAIR"
  | "HISTORICAL_SCREEN_FAILED"
  | "WAIT"
  | "BUY_A_SELL_B"
  | "SELL_A_BUY_B"
  | "PROVIDER_ERROR";

export type CardStatus = "pass" | "caution" | "fail";

export type NarrativeClassification =
  | "NO_OBVIOUS_NEWS_EXPLANATION"
  | "POSSIBLE_COMPANY_SPECIFIC_EXPLANATION"
  | "MIXED"
  | "INSUFFICIENT_NEWS"
  | "AI_UNAVAILABLE";

export type NarrativeConfidence = "LOW" | "MEDIUM" | "HIGH";

export type AiStatus =
  | "ok"
  | "unavailable"
  | "not_configured"
  | "insufficient_news"
  | "recorded";

export type ExitReason = "target" | "stop" | "time" | "end_of_sample";

export type Direction = "SELL_A_BUY_B" | "BUY_A_SELL_B";

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------

export interface AnalyseRequest {
  ticker_a: string;
  ticker_b: string;
  starting_capital: number;
  risk_profile: RiskProfile;
  lookback: Lookback;
  whole_shares: boolean;
  cost_bps: number;
  data_mode: DataMode;
}

export interface NarrativeRequest {
  ticker_a: string;
  ticker_b: string;
  data_mode: DataMode;
}

// ---------------------------------------------------------------------------
// Data metadata
// ---------------------------------------------------------------------------

export interface DataMetadata {
  provider: string;
  retrieved_at: string;
  last_market_date: string;
  currency: string;
  n_common_observations: number;
  is_fixture: boolean;
  fixture_captured_at?: string | null;
  exchange_a?: string | null;
  exchange_b?: string | null;
}

// ---------------------------------------------------------------------------
// Quant blocks
// ---------------------------------------------------------------------------

export interface RelationshipStats {
  correlation: number;
  beta: number;
  intercept: number;
  split_beta_change: number;
  mean_crossings: number;
  leg_weight_a: number;
  leg_weight_b: number;
  formation_start: string;
  formation_end: string;
  evaluation_start: string;
  evaluation_end: string;
}

export interface SignalStats {
  current_spread: number;
  rolling_mean: number;
  rolling_std: number;
  z_score: number;
  as_of_date: string;
  entry_z: number;
  exit_z: number;
  stop_z: number;
  max_holding_days: number;
}

export interface TradeRecord {
  signal_date: string;
  entry_date: string;
  exit_signal_date?: string | null;
  exit_date?: string | null;
  direction: Direction;
  entry_beta: number;
  qty_a: number;
  qty_b: number;
  entry_price_a: number;
  entry_price_b: number;
  exit_price_a?: number | null;
  exit_price_b?: number | null;
  costs: number;
  exit_reason?: ExitReason | null;
  holding_days?: number | null;
  pnl?: number | null;
}

export interface BacktestMetrics {
  n_trades: number;
  net_profit: number;
  net_return: number;
  gross_return: number;
  win_rate?: number | null;
  avg_win?: number | null;
  avg_loss?: number | null;
  profit_factor?: number | null;
  max_drawdown: number;
  avg_holding_days?: number | null;
  total_costs: number;
  screen_passed: boolean;
  limited_evidence: boolean;
  worst_trade_pnl?: number | null;
}

export interface SizingLeg {
  ticker: string;
  side: "BUY" | "SELL";
  shares: number;
  price: number;
  notional: number;
}

export interface SizingResult {
  sized: boolean;
  reason?: string | null;
  legs: SizingLeg[];
  gross_exposure: number;
  net_exposure: number;
  estimated_cost: number;
  stress_loss_estimate: number;
  risk_budget: number;
  max_gross_allowed: number;
  remaining_cash: number;
}

export type EvidenceCardKey =
  | "move_together"
  | "stable_relationship"
  | "unusual_today"
  | "worked_historically";

export interface EvidenceCard {
  key: EvidenceCardKey;
  title: string;
  status: CardStatus;
  headline_value: string;
  detail_lines: string[];
  how_this_works: string;
  plain_english: string;
}

// ---------------------------------------------------------------------------
// Chart series
// ---------------------------------------------------------------------------

export interface SeriesPoint {
  date: string;
  value?: number | null;
}

export interface NormalisedPricesChart {
  a: SeriesPoint[];
  b: SeriesPoint[];
}

export interface SpreadMarker {
  date: string;
  kind: "entry" | "exit";
  direction: Direction;
  z: number;
}

export interface SpreadChart {
  spread: SeriesPoint[];
  rolling_mean: SeriesPoint[];
  upper_entry: SeriesPoint[];
  lower_entry: SeriesPoint[];
  upper_stop: SeriesPoint[];
  lower_stop: SeriesPoint[];
  markers: SpreadMarker[];
  formation_end: string;
}

export interface EquityChart {
  equity: SeriesPoint[];
}

export interface Charts {
  normalised_prices: NormalisedPricesChart;
  spread: SpreadChart;
  equity: EquityChart;
}

// ---------------------------------------------------------------------------
// Analyse response
// ---------------------------------------------------------------------------

export interface AnalyseResponse {
  request: AnalyseRequest;
  data?: DataMetadata | null;
  state: FinalState;
  explanation: string;
  relationship?: RelationshipStats | null;
  signal?: SignalStats | null;
  backtest?: BacktestMetrics | null;
  trades: TradeRecord[];
  sizing?: SizingResult | null;
  evidence_cards: EvidenceCard[];
  charts?: Charts | null;
  warnings: string[];
  methodology_version: string;
}

// ---------------------------------------------------------------------------
// Narrative Lens
// ---------------------------------------------------------------------------

export interface NewsItem {
  source_id: string;
  ticker: string;
  headline: string;
  snippet?: string | null;
  source: string;
  published_at: string;
  url?: string | null;
}

export interface EvidenceClaim {
  claim: string;
  source_ids: string[];
}

export interface NarrativeResponse {
  ai_status: AiStatus;
  model?: string | null;
  classification: NarrativeClassification;
  confidence?: NarrativeConfidence | null;
  summary_a?: string | null;
  summary_b?: string | null;
  shared_story?: string | null;
  risk_flags: string[];
  evidence: EvidenceClaim[];
  explanation?: string | null;
  news_items: NewsItem[];
  elevated_news_risk: boolean;
  recorded_at?: string | null;
}

// ---------------------------------------------------------------------------
// Misc endpoints
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: "ok";
  version: string;
  deepseek_configured: boolean;
}

export interface SymbolSearchResult {
  symbol: string;
  name: string;
  exchange?: string | null;
  currency?: string | null;
}

export interface SymbolSearchResponse {
  results: SymbolSearchResult[];
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown> | null;
}
