# PairScope quant model

This document explains, in plain English, every calculation the quant
engine performs, every threshold it applies, and every judgement call we
made where the specification allowed more than one reading. Every
threshold lives in `backend/app/config.py` (exposed via
`GET /api/methodology`); the names in `CAPITALS` below refer to that file.
The engine itself lives in `backend/app/quant/` and is deterministic:
the same inputs always produce byte-identical outputs.

The whole model uses only school-level statistics: a correlation, a line
of best fit, an average, and a standard deviation. Nothing else.

---

## 0. Canonical ticker order

Before any mathematics, the engine sorts the two tickers alphabetically
(case-insensitive) and fits and simulates in that fixed **canonical**
order. Entering (PEP, KO) or (KO, PEP) is therefore exactly the same
analysis. Every output — direction states, signs, trade legs, sizing
legs, evidence cards, charts — is then mapped back to the order the user
typed, so that the displayed verdict **BUY_A_SELL_B always means "buy the
displayed ticker A and sell the displayed ticker B"**.

What "mapping back" means when the displayed order is the reverse of the
canonical order (all documented decisions):

- **Direction states and trade labels flip**: canonical SELL_A_BUY_B
  becomes displayed BUY_A_SELL_B, and each trade's `qty_a`/`qty_b` and
  entry/exit prices swap slots so `qty_a` always refers to displayed A.
- **Spread, rolling mean and z-score are negated** for display. "A rich"
  in canonical terms is "B rich" in displayed terms, so a displayed
  z-score of +2 always means *displayed A looks expensive relative to
  displayed B* — the on-screen rule "z >= +2 => sell A, buy B" is
  therefore true in whichever order the user typed the pair. The rolling
  standard deviation is unchanged (it has no sign), so the entry/stop
  bands mirror correctly.
- **Beta and intercept are re-expressed for the displayed direction**:
  if the canonical fit is `log A' = c + b·log B'`, the same line read the
  other way is `log A = (-c/b) + (1/b)·log B`. Displaying `beta' = 1/b`
  keeps the schema identities `leg_weight_a = 1/(1+beta)` and
  `leg_weight_b = beta/(1+beta)` true in displayed terms.
- **`split_beta_change` and `mean_crossings` are reported as the
  canonical diagnostics** — they are the exact numbers the suitability
  gate checked (the mean-crossing count is order-independent anyway).
- **Backtest metrics and the equity chart are unchanged** — profit and
  loss do not depend on which stock you typed first.

## 1. Data expectations

The engine receives two cleaned DataFrames from the data layer with an
identical ascending `DatetimeIndex` and adjusted `open`/`close` columns.
Data-level decisions (insufficient data, identical tickers, currency
mismatch, provider errors) are made upstream; the engine only ever sees
valid, aligned data.

## 2. Step one — do they move together?

Daily return: `r_t = close_t / close_{t-1} - 1`.

We compute the **Pearson correlation** of the two daily-return series over
the **full common sample**. The pair passes when correlation is at least
`MIN_CORRELATION` (0.60). Correlation is only a first filter — we never
present it as an edge.

## 3. Step two — what is their normal relationship?

The sample is split chronologically:

- **Formation period** = the first `FORMATION_FRACTION` (60%) of common
  dates. *Documented decision:* the count is **floored**
  (`floor(0.60 · n)` rows), so the formation window never exceeds 60%.
- **Evaluation period** = every remaining date.

Using only formation dates, we fit an ordinary least-squares line between
the natural logs of the adjusted closes (logs compare proportional moves
rather than raw currency moves):

```
log(price A) = intercept + beta · log(price B)
```

`beta` is the relative percentage sensitivity of A to B. It sets the
**notional weights** of the two legs — it is *not* a share ratio:

```
w_A = 1 / (1 + beta)        w_B = beta / (1 + beta)
```

The spread is today's error from that frozen line, computed over the
**full sample** with the frozen formation intercept and beta:

```
spread_t = log(close A_t) - intercept - beta · log(close B_t)
```

### Suitability safeguards (spec order — first failure is the headline reason)

1. Full-sample return correlation >= `MIN_CORRELATION` (0.60).
2. `beta` is finite and strictly positive. (A positive beta supports the
   intuitive direction: when A is expensive relative to B, sell A, buy B.)
3. **Split-beta stability**: refit each half of the formation period;
   require `|beta_h1 - beta_h2| / |beta_full| <= MAX_SPLIT_BETA_CHANGE`
   (50%). *Documented decision:* when this ratio cannot be computed
   (beta of ~0 or a degenerate half-window fit), it is reported as a
   large finite sentinel (999.0) and always fails.
4. Neither leg weight exceeds `MAX_LEG_WEIGHT` (80% of gross exposure),
   i.e. `max(1, beta) / (1 + beta) <= 0.80`.
5. **Mean crossings** >= `MIN_MEAN_CROSSINGS` (6). *Documented decision —
   exact rule:* on every date where the rolling mean of the previous
   `ROLLING_WINDOW` (60) spreads exists (formation tail plus evaluation),
   take the deviation `spread_t - rolling_mean_t` and count strict sign
   changes between consecutive dates. Exact zeros do not count as
   crossings.

Any failure means the state `UNSUITABLE_PAIR`. *Documented decision:*
when beta is valid we still compute the spread, z-scores, backtest and
charts for a failed pair, so the evidence cards can show real values and
the rejection is transparent. When beta itself is invalid, everything
downstream of the spread is skipped and the affected cards show "n/a".

## 4. Step three — is today's gap unusual? (z-score)

For each date with at least `ROLLING_WINDOW` (60) **prior** spread values:

```
z_t = (spread_t - mean(previous 60 spreads)) / std(previous 60 spreads, ddof=1)
```

The current date is **always excluded from its own window** (the window is
the 60 spreads strictly before t). The z-score is simply how many recent
standard deviations today's relationship sits from normal — a ruler for
unusualness, not a prediction guarantee.

**Today's signal is the z-score on the last evaluation date.**

Fixed rules (never parameter-searched):

| Rule | Threshold (config) |
| --- | --- |
| Enter | `|z| >= ENTRY_Z` (2.0) |
| Exit (target) | `|z| <= EXIT_Z` (0.5) |
| Stop | `|z| >= STOP_Z` (3.5) |
| Time stop | `MAX_HOLDING_DAYS` (20 trading days) |

Direction (in displayed terms): `z >= +2` => SELL A, BUY B;
`z <= -2` => BUY A, SELL B; otherwise WAIT.

**No lookahead anywhere**: a value shown for date t uses only the frozen
formation parameters and spread information at or before t. This is
tested by perturbing future prices and asserting earlier values are
byte-identical.

## 5. Step four — did the fixed rule work historically?

A strictly chronological simulation over **evaluation dates only** (dates
the fit never saw), with at most **one open position**:

- The decision is generated from the **close** of day t (that day's z).
- Entries and exits execute at the **open of the next available trading
  day**.
- *Documented decision:* an entry signal on the very last date is dropped
  — there is no next open to execute at.
- *Documented decision — exit precedence* when several rules fire at the
  same close: target first, then stop, then the time limit. (Target and
  stop can never fire together since 0.5 < 3.5.)
- *Documented decision — time stop counting:* holding days are counted
  from the **entry execution date**. The time stop fires at the close of
  the 20th trading day after entry and executes at the next open, so a
  pure time exit shows 21 days held.
- *Documented decision — end of sample:* any position still open at the
  final date is closed **at the final close** (exit reason
  `end_of_sample`), because no next open exists. This is the only
  execution not at an open.

### Position construction

One unit of gross exposure per trade, split by the frozen weights
`w_A = 1/(1+beta)` and `w_B = beta/(1+beta)`. Signed unit quantities are
frozen at the entry open:

```
qty = ± notional_weight / entry_open_price      (per leg)
```

`z >= +2` (canonical A rich): sell canonical A, buy canonical B;
`z <= -2`: the reverse.

### Costs — four cost events per round trip

`cost_bps · 1e-4 · |traded notional|` is charged **separately on each
leg** at entry (entry-price notionals, which total exactly 1 unit of
gross) **and again at exit** (exit-price notionals). Costs are subtracted
from trade PnL.

### Accounting

- Both legs are marked daily at adjusted closes.
- Short-sale proceeds are collateral, never reusable cash.
- Trade PnL (after costs) is a fraction of the trade's 1-unit gross
  exposure. After-cost per-trade returns are **compounded** into an
  equity curve over the evaluation period: equity starts at 1.0, stays
  flat while no position is open, and while a position is open is marked
  daily as `equity_at_entry · (1 + close-to-close PnL - entry cost)`.
  *Documented decision:* the entry cost is included in the daily mark
  from the entry day, so the curve dips by costs immediately.

### Trade ledger and metrics

One shared ledger records signal date, execution date, direction, entry
beta, signed quantities, entry/exit prices, costs, exit reason, holding
days and after-cost PnL. From it we report:

- `n_trades` — completed trades (every entered trade completes, because
  of the end-of-sample close).
- `net_profit` — sum of after-cost trade PnL.
- `net_return` — compounded equity end minus 1 (after costs);
  `gross_return` — the same compounding before costs.
- `win_rate`, `avg_win`, `avg_loss`.
- `profit_factor` = (sum of winning trade PnL) / |sum of losing trade
  PnL|, using **after-cost** PnL. *Documented decision:* with no losing
  trades it is undefined (`null` in the API; the UI shows "n/a — no
  losing trades") and the gate treats it as a pass provided at least one
  trade won.
- `max_drawdown` — worst peak-to-trough fall of the **daily** equity
  curve (a negative number).
- `avg_holding_days`, `total_costs`, `worst_trade_pnl`.

### The minimum screen gate (a product decision, not proof of future profit)

The screen **passes** only when all four hold:

| Gate | Threshold (config) |
| --- | --- |
| Completed trades | `>= MIN_TRADES` (5) |
| Net profit after costs | `> 0` |
| Profit factor | `> MIN_PROFIT_FACTOR` (1.0) |
| Max drawdown | `>= MAX_DRAWDOWN_LIMIT` (-20%) |

With 5–9 trades (`MIN_TRADES` up to `LIMITED_EVIDENCE_TRADES - 1`), the
result is flagged **limited evidence** even when it passes — five trades
are never called statistically reliable.

## 6. Final decision order

After the data layer's states (provider error, insufficient data,
identical tickers / currency mismatch), the engine decides in this order:

1. `UNSUITABLE_PAIR` — any suitability safeguard failed.
2. `HISTORICAL_SCREEN_FAILED` — the backtest gate failed.
3. `WAIT` — today's `|z| < ENTRY_Z`. *Documented decision:* if today's
   z-score cannot be computed at all, the engine also returns WAIT with a
   warning.
4. Otherwise the direction implied by the z-score, mapped to the
   displayed order.

The backend is the single source of truth; the frontend only renders.

## 7. Position sizing (actionable states only)

Sizing runs **only** for BUY_A_SELL_B / SELL_A_BUY_B; every other state
returns no sizing block. The user-facing story: *use the line-of-best-fit
ratio, fit the pair inside our money limit, then scale it down if the
stop could lose more than our risk allowance.*

Risk profiles (`RISK_PROFILES`):

| Profile | Max gross exposure | Max stress loss |
| --- | ---: | ---: |
| Conservative | 50% of capital | 0.5% of capital |
| Balanced | 75% of capital | 1.0% of capital |
| Aggressive | 100% of capital | 2.0% of capital |

Let `G = capital · max_gross_fraction`. Target notionals (canonical,
then mapped): `A: G/(1+beta)`, `B: beta·G/(1+beta)`. Shares come from the
**latest adjusted close** prices.

**Stress loss estimate** = |worst historical losing trade PnL| (a
fraction of gross) × proposed gross exposure. With no losing trade, a
conservative `STRESS_FALLBACK_FRACTION` (3% of gross) is used and a
warning is attached. *Documented decision:* because the stress estimate
scales linearly with gross exposure, "scale down proportionally until the
stress fits" is implemented exactly as capping the allowed gross at
`min(G, stress_budget / stress_fraction)` before computing shares; the
constraint is re-checked on the final rounded quantities.

- **Whole-share mode**: a bounded search within
  `WHOLE_SHARE_SEARCH_RADIUS` (3) shares of the rounded target quantities
  (never below 1 share per leg). Feasible = gross exposure fits inside
  the allowed gross (which already folds in both the gross cap and the
  stress budget). Among feasible candidates we pick the one whose
  notional ratio is closest to the target ratio in log space;
  *documented tie-breaks:* larger gross exposure first (use more of the
  budget), then fewer A shares — fully deterministic. If nothing in the
  search box is feasible, the minimum pair (1 share of each leg) is
  tested; if even that breaches the limits, `sized = false` is returned
  with a plain-English reason.
- **Fractional mode**: shares rounded to `FRACTIONAL_DECIMALS` (4).
  *Documented decision:* if half-up rounding nudges the total a hair over
  the limit, the quantities are floored at 4 decimals instead, so the
  limits are never breached.

Reported fields: both legs (ticker, side, shares, price, notional), gross
exposure, net exposure (buy notional − sell notional), estimated cost
(`cost_bps` on both **entry** legs), stress loss estimate, risk budget,
max allowed gross, and remaining cash = capital − gross exposure.
*Documented decision:* short proceeds are treated as reserved collateral,
so the short leg consumes capital like the long leg — no leverage beyond
the profile's gross cap, ever. The stress estimate is not a guaranteed
maximum loss: prices can gap and history can be exceeded.

## 8. Evidence cards

Exactly four cards, in checklist order, each showing measured values AND
thresholds, a "How this works" tooltip and a plain-English line:

1. **move_together** — correlation vs `MIN_CORRELATION`. Pass/fail only
   (the spec defines a strict threshold, so no caution band).
2. **stable_relationship** — beta, split-beta change, largest leg weight,
   mean crossings, each with its limit. Pass/fail only.
3. **unusual_today** — current z vs `ENTRY_Z`. *Documented caution band:*
   **caution when `|z|` is at least 75% of `ENTRY_Z` but below it**
   (1.5–2.0 with defaults) — "stretched but not actionable"; pass at or
   above `ENTRY_Z`; fail below the caution band. The 0.75 factor is
   derived from `ENTRY_Z`, not an independent knob.
4. **worked_historically** — trade count, net profit, profit factor and
   drawdown vs their gates. **Caution when the screen passed with limited
   evidence (5–9 trades)**; pass when passed with 10+; fail otherwise.

## 9. Charts

All series use `YYYY-MM-DD` date strings and daily points (no
downsampling).

1. **Normalised prices** — both stocks rebased to 100 at the first common
   date, full sample.
2. **Spread and signal** — full-sample spread, previous-60-day rolling
   mean, entry bands (mean ± `ENTRY_Z`·std) and stop bands (mean ±
   `STOP_Z`·std). Rolling series exist **only where the 60-day window
   exists** (no fabricated early values). Entry/exit markers come from
   the trade ledger, placed at **execution dates** with the z-score of
   the signal that caused them (*documented decision:* end-of-sample
   exits show the z at the exit date since they had no exit signal).
   `formation_end` marks the formation/evaluation boundary.
3. **Backtest equity** — the after-cost evaluation-period curve starting
   at 1.0. Max drawdown is a summary metric, not a fourth chart.

## 10. Honesty rules baked into the engine

- Fixed thresholds; no parameter search, ever.
- Costs on all four legs of every round trip.
- Next-open execution — never trade the price that generated the signal.
- Formation parameters frozen before the evaluation period begins.
- Passing the screen is called a *minimum screen*, never proof of profit.
- All numbers in the API are finite (no NaN/Infinity); anything
  uncomputable is `null` with a plain-English warning.
