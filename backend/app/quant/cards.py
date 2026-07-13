"""Section 6 of the spec: the four evidence cards.

The analysis should feel like an auditable checklist. Every card shows the
measured value AND the threshold it was judged against, a "How this works"
tooltip, and a plain-English one-liner. All values arrive here already in
the user's DISPLAYED ticker order.

Caution bands (documented in docs/MODEL.md):
- unusual_today shows CAUTION when |z| is at least 75% of the entry
  threshold but below it (1.5 to 2.0 with the default ENTRY_Z of 2.0).
- worked_historically shows CAUTION when the screen passed on limited
  evidence (5-9 completed trades).
- move_together and stable_relationship are strict pass/fail checks in the
  spec, so they never show caution.
"""

from __future__ import annotations

from app import config
from app.schemas import BacktestMetrics, CardStatus, EvidenceCard, SignalStats

from .relationship import Suitability

# Caution band for "unusual today": within this fraction of the entry
# threshold counts as "getting close". Derived from config, not a new knob.
UNUSUAL_CAUTION_FRACTION = 0.75


def build_cards(
    *,
    ticker_a: str,
    ticker_b: str,
    correlation: float,
    beta: float,
    split_beta_change: float,
    mean_crossings: int,
    leg_weight_a: float,
    leg_weight_b: float,
    suitability: Suitability,
    signal: SignalStats | None,
    metrics: BacktestMetrics | None,
) -> list[EvidenceCard]:
    """Build exactly four cards, in checklist order."""
    return [
        _move_together_card(ticker_a, ticker_b, correlation, suitability),
        _stable_relationship_card(
            beta, split_beta_change, mean_crossings, leg_weight_a, leg_weight_b, suitability
        ),
        _unusual_today_card(ticker_a, ticker_b, signal),
        _worked_historically_card(metrics),
    ]


def _move_together_card(
    ticker_a: str, ticker_b: str, correlation: float, suitability: Suitability
) -> EvidenceCard:
    status = CardStatus.PASS if suitability.corr_ok else CardStatus.FAIL
    plain = (
        f"The daily percentage moves of {ticker_a} and {ticker_b} lined up strongly."
        if suitability.corr_ok
        else f"The daily percentage moves of {ticker_a} and {ticker_b} did not line up "
        "strongly enough to treat them as a pair."
    )
    return EvidenceCard(
        key="move_together",
        title="Do they move together?",
        status=status,
        headline_value=f"{correlation:.2f} / 1.00",
        detail_lines=[
            f"Daily-return correlation: {correlation:.2f}",
            f"Pass threshold: at least {config.MIN_CORRELATION:.2f}",
        ],
        how_this_works=(
            "We measure the Pearson correlation of the two stocks' daily percentage "
            "moves over the formation window (the first 60% of dates). Values near 1 "
            "mean they usually move in the same direction on the same day; this is "
            "only a first filter, never an edge."
        ),
        plain_english=plain,
    )


def _stable_relationship_card(
    beta: float,
    split_beta_change: float,
    mean_crossings: int,
    leg_weight_a: float,
    leg_weight_b: float,
    suitability: Suitability,
) -> EvidenceCard:
    ok = (
        suitability.beta_ok
        and suitability.split_ok
        and suitability.leg_ok
        and suitability.crossings_ok
    )
    status = CardStatus.PASS if ok else CardStatus.FAIL
    max_leg = max(leg_weight_a, leg_weight_b)
    plain = (
        "The line-of-best-fit relationship looks steady enough to use for a paper trade."
        if ok
        else "The line-of-best-fit relationship is not steady enough to rely on."
    )
    return EvidenceCard(
        key="stable_relationship",
        title="Is the relationship steady?",
        status=status,
        headline_value=f"balance ratio {beta:.2f}",
        detail_lines=[
            f"Hedge ratio (beta): {beta:.3f} (must be a positive, finite number)",
            (
                f"Beta change between formation halves: {split_beta_change:.0%} "
                f"(limit {config.MAX_SPLIT_BETA_CHANGE:.0%})"
            ),
            f"Largest leg weight: {max_leg:.0%} of gross (limit {config.MAX_LEG_WEIGHT:.0%})",
            (
                f"Spread crossed its rolling average {mean_crossings} times "
                f"(minimum {config.MIN_MEAN_CROSSINGS})"
            ),
        ],
        how_this_works=(
            "Beta is the slope of the line of best fit between the two log prices: how "
            "much of B normally balances A. We check that it is positive, that it did not "
            "change dramatically while we were estimating it, that neither leg dominates "
            "the money, and that the spread genuinely oscillates around its average."
        ),
        plain_english=plain,
    )


def _unusual_today_card(
    ticker_a: str, ticker_b: str, signal: SignalStats | None
) -> EvidenceCard:
    caution_z = UNUSUAL_CAUTION_FRACTION * config.ENTRY_Z
    if signal is None:
        return EvidenceCard(
            key="unusual_today",
            title="Is today's gap unusual?",
            status=CardStatus.FAIL,
            headline_value="n/a",
            detail_lines=[
                "Today's z-score could not be computed for this pair.",
                f"Entry threshold: |z| >= {config.ENTRY_Z:.1f}",
            ],
            how_this_works=_Z_TOOLTIP,
            plain_english="Today's gap could not be measured, so there is nothing to act on.",
        )
    z = signal.z_score
    if abs(z) >= config.ENTRY_Z:
        status = CardStatus.PASS
        rich, cheap = (ticker_a, ticker_b) if z > 0 else (ticker_b, ticker_a)
        plain = (
            f"Today's gap is unusually wide: {rich} looks expensive relative to {cheap} "
            f"by about {abs(z):.1f} recent standard deviations."
        )
    elif abs(z) >= caution_z:
        status = CardStatus.CAUTION
        plain = (
            "Today's gap is stretched but has not reached the entry threshold yet — "
            "one to watch, not to act on."
        )
    else:
        status = CardStatus.FAIL
        plain = "Today's gap is within its normal range, so there is nothing unusual to act on."
    return EvidenceCard(
        key="unusual_today",
        title="Is today's gap unusual?",
        status=status,
        headline_value=f"{abs(z):.1f}x the usual drift",
        detail_lines=[
            f"Current z-score: {z:+.2f} (as of {signal.as_of_date})",
            (
                f"Entry threshold: |z| >= {config.ENTRY_Z:.1f} "
                f"(caution from |z| >= {caution_z:.2f})"
            ),
            (
                f"Spread {signal.current_spread:.4f} vs rolling mean "
                f"{signal.rolling_mean:.4f} (std {signal.rolling_std:.4f})"
            ),
        ],
        how_this_works=_Z_TOOLTIP,
        plain_english=plain,
    )


_Z_TOOLTIP = (
    "The z-score counts how many recent standard deviations today's spread sits from "
    f"its previous {config.ROLLING_WINDOW}-day average. It is a ruler for unusualness, "
    "not a prediction guarantee."
)


def _worked_historically_card(metrics: BacktestMetrics | None) -> EvidenceCard:
    if metrics is None:
        return EvidenceCard(
            key="worked_historically",
            title="Did the rule work in the past?",
            status=CardStatus.FAIL,
            headline_value="n/a",
            detail_lines=[
                "The historical simulation was not run because the relationship "
                "check failed first.",
            ],
            how_this_works=_BACKTEST_TOOLTIP,
            plain_english="There is no usable relationship, so history could not be tested.",
        )
    if metrics.screen_passed and metrics.limited_evidence:
        status = CardStatus.CAUTION
        plain = (
            f"The unchanged rule cleared the minimum screen after costs, but with only "
            f"{metrics.n_trades} trades this is limited evidence, not statistical proof."
        )
    elif metrics.screen_passed:
        status = CardStatus.PASS
        plain = (
            "The unchanged rule cleared the minimum historical screen after costs on "
            "later dates the fit never saw."
        )
    else:
        status = CardStatus.FAIL
        plain = (
            "The unchanged rule did not clear the minimum historical screen after "
            "costs, so no trade is proposed."
        )
    profit_factor_line = (
        f"Profit factor: {metrics.profit_factor:.2f} (must be above "
        f"{config.MIN_PROFIT_FACTOR:.1f})"
        if metrics.profit_factor is not None
        else (
            "Profit factor: n/a - no losing trades (must be above "
            f"{config.MIN_PROFIT_FACTOR:.1f})"
        )
    )
    detail_lines = [
        f"Completed trades: {metrics.n_trades} (minimum {config.MIN_TRADES})",
        f"Net profit after costs: {metrics.net_profit:+.2%} of gross exposure (must be > 0)",
        profit_factor_line,
        (
            f"Max drawdown: {metrics.max_drawdown:.1%} "
            f"(limit {config.MAX_DRAWDOWN_LIMIT:.0%})"
        ),
        f"Total estimated costs: {metrics.total_costs:.2%} of gross exposure",
    ]
    if metrics.limited_evidence:
        detail_lines.append(
            f"Limited evidence: {config.MIN_TRADES}-{config.LIMITED_EVIDENCE_TRADES - 1} "
            "trades is too few to call reliable."
        )
    return EvidenceCard(
        key="worked_historically",
        title="Did the rule work in the past?",
        status=status,
        headline_value=f"{metrics.n_trades} trades, net {metrics.net_profit:+.1%}",
        detail_lines=detail_lines,
        how_this_works=_BACKTEST_TOOLTIP,
        plain_english=plain,
    )


_BACKTEST_TOOLTIP = (
    "We replay the identical fixed rule over the most recent 40% of dates, which were "
    "never used to fit the relationship. Signals form at a close, execute at the next "
    "open, and costs are charged on both legs at entry and exit. Passing this screen "
    "is a minimum requirement, not proof of future profit."
)
