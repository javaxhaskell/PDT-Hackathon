"""PairScope frozen configuration.

Every quant threshold lives here and only here. The /api/methodology
endpoint exposes these values, and the UI displays the relevant ones.
Changing a value here changes the whole product; nothing else may
hard-code a threshold.
"""

from __future__ import annotations

import os

METHODOLOGY_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Data requirements
# ---------------------------------------------------------------------------
# Minimum common trading observations required per lookback request.
MIN_OBS_ONE_YEAR = 252
MIN_OBS_LONGER = 400

# Live responses are cached for this many seconds.
PRICE_CACHE_TTL_SECONDS = 15 * 60
NEWS_CACHE_TTL_SECONDS = 15 * 60
NARRATIVE_CACHE_TTL_SECONDS = 60 * 60

# Conservative staleness rule (calendar days). We do not model exchange
# holiday calendars; instead we allow weekends plus public holidays by
# treating data as stale only when the last market date is more than
# STALE_CALENDAR_DAYS calendar days ago.
STALE_CALENDAR_DAYS = 7

# ---------------------------------------------------------------------------
# Step 1 — do they move together?
# ---------------------------------------------------------------------------
MIN_CORRELATION = 0.60

# ---------------------------------------------------------------------------
# Step 2 — normal relationship (formation OLS fit)
# ---------------------------------------------------------------------------
FORMATION_FRACTION = 0.60          # first 60% of common dates fit the line
MAX_LEG_WEIGHT = 0.80              # neither leg may exceed 80% of gross
MIN_MEAN_CROSSINGS = 6             # spread must cross its rolling mean >= 6x
MAX_SPLIT_BETA_CHANGE = 0.50       # halves of formation beta may differ <= 50%
                                   # relative to the full-formation beta

# ---------------------------------------------------------------------------
# Step 3 — z-score signal rules (fixed; never parameter-searched)
# ---------------------------------------------------------------------------
ROLLING_WINDOW = 60                # previous 60 spreads, excluding today
ENTRY_Z = 2.0
EXIT_Z = 0.5
STOP_Z = 3.5
MAX_HOLDING_DAYS = 20

# ---------------------------------------------------------------------------
# Step 4 — historical screen gate
# ---------------------------------------------------------------------------
MIN_TRADES = 5
LIMITED_EVIDENCE_TRADES = 10       # 5..9 completed trades => "Limited evidence"
MIN_PROFIT_FACTOR = 1.0
MAX_DRAWDOWN_LIMIT = -0.20         # max drawdown no worse than -20%
DEFAULT_COST_BPS = 10.0            # per leg per transaction

# ---------------------------------------------------------------------------
# Sizing and risk profiles
# ---------------------------------------------------------------------------
RISK_PROFILES = {
    "conservative": {"max_gross_fraction": 0.50, "max_stress_fraction": 0.005},
    "balanced": {"max_gross_fraction": 0.75, "max_stress_fraction": 0.010},
    "aggressive": {"max_gross_fraction": 1.00, "max_stress_fraction": 0.020},
}
STRESS_FALLBACK_FRACTION = 0.03    # if no losing trade in evaluation period
FRACTIONAL_DECIMALS = 4
WHOLE_SHARE_SEARCH_RADIUS = 3      # bounded search around rounded quantities

DEFAULT_STARTING_CAPITAL = 10_000.0
DEFAULT_LOOKBACK = "2y"
LOOKBACKS = ("1y", "2y", "3y")

# ---------------------------------------------------------------------------
# News / Narrative Lens
# ---------------------------------------------------------------------------
MAX_NEWS_ITEMS_PER_TICKER = 8
NEWS_LOOKBACK_DAYS = 30
MIN_USABLE_NEWS_ITEMS = 2          # per company, else INSUFFICIENT_NEWS
MAX_EVIDENCE_CLAIMS = 3
MAX_EXPLANATION_WORDS = 70

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_TIMEOUT_SECONDS = 20.0
DEEPSEEK_MAX_RETRIES = 1           # at most one retry
DEEPSEEK_TEMPERATURE = 0.1
# Large enough for the bounded reply (two summaries, <=3 claims, <=70-word
# explanation) with headroom — a too-small cap truncates the JSON mid-string.
DEEPSEEK_MAX_OUTPUT_TOKENS = 1500

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
# Origins are normalised (trailing slash stripped) because browser Origin
# headers never carry one and the CORS match must be character-exact.
CORS_ORIGINS = [
    o.strip().rstrip("/")
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]


def methodology() -> dict:
    """Serializable snapshot of every frozen threshold for /api/methodology."""
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "data": {
            "min_obs_one_year": MIN_OBS_ONE_YEAR,
            "min_obs_longer": MIN_OBS_LONGER,
            "price_cache_ttl_seconds": PRICE_CACHE_TTL_SECONDS,
            "stale_calendar_days": STALE_CALENDAR_DAYS,
        },
        "correlation": {"min_correlation": MIN_CORRELATION},
        "relationship": {
            "formation_fraction": FORMATION_FRACTION,
            "max_leg_weight": MAX_LEG_WEIGHT,
            "min_mean_crossings": MIN_MEAN_CROSSINGS,
            "max_split_beta_change": MAX_SPLIT_BETA_CHANGE,
        },
        "signal": {
            "rolling_window": ROLLING_WINDOW,
            "entry_z": ENTRY_Z,
            "exit_z": EXIT_Z,
            "stop_z": STOP_Z,
            "max_holding_days": MAX_HOLDING_DAYS,
        },
        "backtest_gate": {
            "min_trades": MIN_TRADES,
            "limited_evidence_trades": LIMITED_EVIDENCE_TRADES,
            "min_profit_factor": MIN_PROFIT_FACTOR,
            "max_drawdown_limit": MAX_DRAWDOWN_LIMIT,
            "default_cost_bps": DEFAULT_COST_BPS,
        },
        "sizing": {
            "risk_profiles": RISK_PROFILES,
            "stress_fallback_fraction": STRESS_FALLBACK_FRACTION,
            "fractional_decimals": FRACTIONAL_DECIMALS,
            "whole_share_search_radius": WHOLE_SHARE_SEARCH_RADIUS,
        },
        "narrative": {
            "max_news_items_per_ticker": MAX_NEWS_ITEMS_PER_TICKER,
            "news_lookback_days": NEWS_LOOKBACK_DAYS,
            "min_usable_news_items": MIN_USABLE_NEWS_ITEMS,
            "max_evidence_claims": MAX_EVIDENCE_CLAIMS,
            "max_explanation_words": MAX_EXPLANATION_WORDS,
            "model_env": "DEEPSEEK_MODEL",
        },
    }
