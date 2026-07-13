# PairScope — the ten-minute presentation

One presenter drives the app; a second can hold the cheat sheet and watch the
clock. Rehearsal target: **under nine minutes**, leaving at least one minute
of contingency. Use **fixture mode** for the judged demo unless live data has
been tested immediately beforehand.

---

## The script

### 0:00 – 1:00 — The problem

> "Some pairs of stocks are economically joined at the hip — think Coca-Cola
> and Pepsi. They usually move together, but sometimes they drift apart
> temporarily. That drift is either noise that snaps back, or news that
> doesn't.
>
> PairScope answers three questions about any two tickers: does the current
> gap look statistically unusual, did a fixed trading rule pass a minimum
> historical screen after realistic costs, and does recent news suggest the
> gap is temporary or fundamentally explained?
>
> It's an educational research tool. It never claims guaranteed profit, never
> sends an order, and never touches a brokerage."

### 1:00 – 2:45 — The model (one simple visual, five steps)

Show the spread chart (or the model diagram) and count the steps on your
fingers:

> "The whole model is school-level statistics — a straight line, an average
> and a standard deviation. Five steps:
>
> **One** — we check that their daily returns actually moved together.
> Correlation has to be at least 0.60 or we stop right there.
>
> **Two** — we draw a line of best fit between their log prices. The slope,
> beta, tells us how much of stock B normally balances stock A.
>
> **Three** — we measure today's distance from that line. We call that
> distance the spread — it's today's error from their normal relationship.
>
> **Four** — we express that distance as a z-score against the previous 60
> days. A z-score of 2 means the gap is about two recent standard deviations
> from normal. It is a ruler for unusualness, not a prediction guarantee.
>
> **Five** — and this is the honest part — we learn the relationship on the
> first 60 percent of dates only, then simulate the unchanged rule on the
> later 40 percent that the fit never saw. Signals form at a close; execution
> happens at the next day's open; costs are charged on every leg."

### 2:45 – 6:30 — Live product demo (KO / PEP, fixture mode)

One pre-validated recorded pair, one concise route, seven beats:

1. **Enter the pair.** Type `KO` and `PEP`, leave starting capital at
   10,000, fixture mode on. Point out the *Recorded market snapshot* banner:
   > "We're demoing on a frozen snapshot of real market data so the result is
   > deterministic — the same provider interface runs live yfinance data."
2. **Verdict and the four evidence cards.**
   > "The verdict is one machine-readable state from the backend, and these
   > four cards are the audit trail: do they move together, is the
   > relationship stable enough, is today unusual, and did the fixed rule
   > work historically after costs. Pass, caution or fail — no black box."
3. **Spread chart, z-score, direction.** Point at today's point beyond the
   entry band:
   > "Here's the spread against its ±2 standard-deviation entry bands and the
   > 3.5 stop bands. Today's z-score is above 2, so the rule says Coca-Cola
   > is unusually expensive relative to Pepsi: sell KO, buy PEP — as a paper
   > trade."
4. **Flip risk profiles.** Switch Conservative → Aggressive:
   > "Sizing is just: fit both legs inside the money limit using the
   > line-of-best-fit ratio, then scale down until the stress-loss estimate
   > fits the risk budget. Watch the share counts change with the profile."
5. **One-line backtest summary.**
   > "On the 40 percent of dates the fit never saw: seven completed trades,
   > net positive after costs, profit factor above one, drawdown inside
   > limits — and the app itself labels seven trades as *limited evidence*."
6. **Open the Narrative Lens.**
   > "The model tells us whether the gap is unusual; DeepSeek helps us
   > examine why. It reads only the headlines we hand it — it never sees the
   > trade and never calculates anything."
7. **Two cited headlines, max.** Point at a claim and its linked sources:
   > "Every claim is pinned to a supplied source ID — invented citations get
   > stripped server-side. Here the news shows no obvious company-specific
   > explanation, which is what you want to see for a mean-reversion setup."

Keep normalised prices, the detailed equity history and extra metrics in
their expandable sections — open them only if a judge asks.

### 6:30 – 7:45 — Risk and honesty

> "What could go wrong, and what did we deliberately model?
>
> Costs: 10 basis points per leg per transaction — that's four charged legs
> per round trip. Execution: a signal at the close executes at the next day's
> open, so we never trade on a price we couldn't have had. Protection: a stop
> at a z-score of 3.5, a forced exit after 20 trading days, a gross-exposure
> cap and a stress-loss budget per risk profile.
>
> And the honest caveats: historical relationships can break — if these two
> businesses genuinely diverge, the spread never comes back and the stop is
> what limits the damage. Short selling has real-world constraints — borrow
> fees, availability, dividends on shorts — that we estimate but don't fully
> model.
>
> The AI can be wrong too. It sees only the headlines we supply, it can
> misread them, and that's exactly why it never calculates the trade or the
> share quantities — it's a context layer, not a signal."

### 7:45 – 9:15 — Why this is credible

> "Why should you trust what you just saw?"

- **Deterministic quant, visibly separate AI.** Arithmetic proposes the paper
  trade; language analysis only flags reasons for caution.
- **No future-data leakage.** The fit is frozen on the first 60% of dates;
  every rolling value uses only prior data; tests enforce it.
- **Costs on all four trade legs** — both legs at entry and both at exit.
- **Fixed thresholds, no parameter hunting.** Entry 2.0, exit 0.5, stop 3.5,
  20 days — frozen in one config file and shown in the UI. Nothing was tuned
  to make the demo pass.
- **Automated tests** cover signals, timing, leakage, sizing, sign
  consistency and AI failure modes.
- **Transparent rejection.** Unsuitable pairs fail loudly with the reason —
  we can demo an honest rejection on NVDA/KO.
- **Grounded AI output**: structured JSON, Pydantic-validated, every claim
  linked to supplied source IDs.
- **Graceful degradation**: if DeepSeek is down, the quant analysis is fully
  usable and the AI card says so.

### 9:15 – 10:00 — Close

> "PairScope does not promise the future. It turns a trading idea into a
> transparent, testable and risk-sized decision that anyone can inspect.
> Thank you — happy to take questions."

---

## One-page presenter cheat sheet

**The sentence:** PairScope finds two stocks that usually move together,
measures how unusual their current gap is, checks whether a fixed past rule
worked after costs, sizes an understandable two-leg paper trade, and uses AI
to investigate whether news may explain the gap.

**The pitch line:** the numbers tell us whether the gap is unusual; the AI
helps us investigate why.

| Number | Value |
| --- | --- |
| Correlation threshold | ≥ 0.60 |
| Formation / evaluation split | first 60% / final 40% |
| Rolling z-score window | previous 60 days (excluding today) |
| Entry / exit / stop z | 2.0 / 0.5 / 3.5 |
| Max holding | 20 trading days |
| Backtest gate | ≥ 5 trades, net profit > 0, profit factor > 1.0, drawdown ≥ −20% |
| Limited evidence | 5–9 trades |
| Costs | 10 bps per leg per transaction (4 charged legs per round trip) |
| Risk profiles (gross / stress) | Cons. 50%/0.5% · Bal. 75%/1.0% · Agg. 100%/2.0% |
| Stress fallback (no losing trade) | 3% of gross |

**Directions:** z ≥ +2 → SELL A, BUY B (A expensive). z ≤ −2 → BUY A, SELL B
(A cheap). Otherwise WAIT.

**Sizing in one breath:** use the line-of-best-fit ratio, fit the pair inside
our money limit, then scale it down if the stop could lose more than our risk
allowance.

**Demo route:** KO + PEP → fixture mode → verdict + 4 cards → spread chart →
flip risk profile → one-line backtest → Narrative Lens → 2 cited headlines.
Backup rejection demo: NVDA + KO.

**Never say:** "guaranteed", "alpha", "this will make money", "the AI
predicts". **Always say:** "paper trade", "historical screen", "candidate to
re-check", "educational tool".

**If a chart question goes deep:** open the expandable sections — normalised
prices and after-cost equity are one click away.

---

## Likely judge questions — with short answers

1. **Why these two stocks?**
   Coca-Cola and Pepsi are a classic economically linked pair — same sector,
   same demand drivers — so their relationship is plausible before we measure
   anything. But nothing is hard-coded: any two same-currency tickers go
   through identical checks, and unsuitable pairs are rejected with reasons.

2. **Why isn't correlation enough?**
   Correlation only says their daily moves lined up historically. It says
   nothing about whether today's gap is unusual, whether the relationship is
   stable, or whether acting on gaps ever worked after costs. It's our first
   filter, never the edge.

3. **What does beta mean?**
   Beta is the slope of the line of best fit between their log prices: the
   relative percentage sensitivity of A to B. We use it to set the notional
   weights of the two legs — it's a money ratio, not a share ratio.

4. **What does a z-score mean?**
   A z-score of 2 means the gap is about two recent standard deviations from
   normal. It is a ruler for unusualness, not a prediction guarantee.

5. **How did you avoid looking into the future?**
   Three ways: the line is fitted only on the first 60% of dates and then
   frozen; every rolling mean and standard deviation uses only the previous
   60 days, excluding today; and a signal formed at a close executes at the
   next day's open. Automated tests assert all three.

6. **Did you include costs?**
   Yes — a configurable estimate, default 10 basis points per leg per
   transaction, charged on both legs at entry and both legs at exit: four
   cost events per round trip. We report results before and after costs, and
   we're clear that spreads, borrow fees and taxes are not fully modelled.

7. **What happens if the relationship breaks?**
   Then the spread doesn't revert and the trade loses. That's the core risk.
   The stop at z = 3.5, the 20-day forced exit and the stress-loss budget cap
   the paper damage, and the stability checks (split-beta change, mean
   crossings) reject pairs whose relationship already looks broken.

8. **Why should we trust the backtest?**
   Cautiously. It runs only on the final 40% of dates the fit never saw, with
   fixed thresholds — no parameter search — next-open execution and costs on
   every leg. It's a minimum screen, a product decision — not proof of future
   profit, and 5–9 trades are explicitly labelled limited evidence.

9. **Why use an LLM at all?**
   The numbers can say a gap is unusual but never why. The LLM reads recent
   headlines and classifies whether news might explain the gap — the one
   thing arithmetic can't do. It's a context layer: it never calculates the
   trade, direction or size.

10. **Can the LLM hallucinate?**
    Yes, so we constrain it: it sees only supplied headlines as structured
    data, must return strict JSON that we validate with Pydantic, and may
    only cite supplied source IDs — invented citations are stripped
    server-side. Every claim is displayed beside its source so a human can
    check it. If it fails, the quant result stands alone.

11. **Why didn't you use embeddings in the first version?**
    The documented DeepSeek capability we rely on is chat completion with
    JSON output — embeddings aren't guaranteed. Exact and token-overlap
    deduplication already handles duplicate headlines, so embeddings would
    add infrastructure without a demonstrated benefit. We'd add them only for
    headline clustering, never as a trade signal.

---

## Backup demo route (if the internet fails)

Fixture mode is the internet-free path — it is the *primary* judged demo, so
a network failure changes almost nothing:

1. Everything runs on localhost: backend :8000, frontend :3000. No external
   calls are needed in fixture mode.
2. `KO` / `PEP` with `data_mode: fixture` replays the frozen recorded market
   snapshot — deterministic verdict, cards, charts and sizing, with the
   *Recorded market snapshot* banner visible. Say what it is: a frozen
   snapshot of real provider data, never hand-edited.
3. The Narrative Lens uses the recorded DeepSeek fixture, labelled *Recorded
   AI response* with its model name and capture time. Say: "this is a
   recorded response from the live integration, replayed for reliability."
4. `NVDA` / `KO` in fixture mode demos the honest rejection path.
5. If the frontend itself fails, open the backend's `/docs` OpenAPI page and
   execute `POST /api/analyse` with the fixture request — the JSON verdict,
   cards and metrics still tell the story.
6. Last resort: screenshots of the analysed pair captured at rehearsal
   (store them in `docs/` before the demo day).

If live mode is shown at all, test it immediately beforehand and mention that
the same provider interface supports live yfinance data.

---

## Rehearsal checklist (target: under nine minutes)

Run the full script against the clock at least twice. Tick everything:

- [ ] Full run-through timed **under 9:00** (leaves 1+ minute contingency).
- [ ] Timer visible to the co-presenter; hard checkpoint: demo starts by 2:45
      and ends by 6:30.
- [ ] `make dev` started fresh; backend :8000 and frontend :3000 both up
      **before** the presentation begins.
- [ ] `GET /api/health` returns `ok`; note whether `deepseek_configured` is
      true so the AI beat matches reality.
- [ ] KO/PEP fixture analysis pre-clicked once — verdict, four cards, spread
      chart, sizing and Narrative Lens all render.
- [ ] Risk-profile flip rehearsed: know which share counts change and roughly
      to what.
- [ ] NVDA/KO rejection route rehearsed as the honest-failure answer.
- [ ] Narrative Lens state known in advance: live `ok`, `recorded`, or
      unavailable — and the matching sentence rehearsed for each.
- [ ] The two headlines you will point at chosen in advance.
- [ ] Z-score ruler line and closing line memorised verbatim.
- [ ] Cheat-sheet numbers drilled: 0.60, 60/40, 60-day window, 2.0/0.5/3.5,
      20 days, gate of 5 trades / PF > 1 / −20%, 10 bps × 4 legs.
- [ ] Each presenter can answer all eleven judge questions unprompted.
- [ ] Laptop: notifications off, display sleep off, browser zoom set so the
      verdict and cards are legible from the back of the room.
- [ ] Backup screenshots captured and stored in `docs/`.
- [ ] Offline drill done once: Wi-Fi disabled, full fixture demo still works.
