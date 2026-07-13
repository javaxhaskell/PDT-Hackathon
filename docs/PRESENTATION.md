# PairScope — the ten-minute presentation

One presenter drives the app; a second can hold the cheat sheet and watch the
clock. Rehearsal target: **under nine minutes**, leaving at least one minute
of contingency. Use **Demo mode** (the recorded fixture snapshot) for the
judged demo unless live data has been tested immediately beforehand.

**The audience is non-finance.** Lead with the plain-English UI — the "In
plain English" story strip, the four question-cards and the "x times the
usual drift" language — and translate every number the moment you say it.

The judged demo has **two beats**: the fun hook is **RCL / CCL** (Royal
Caribbean / Carnival — the cruise-line rivals, an honest *Watch* verdict) and
the green light is **ALL / TRV** (Allstate / Travelers — two large US
property-and-casualty insurers, a *Candidate setup*). The honest-rejection
pair is **KO / PEP**, with **NVDA / KO** as a second, more obvious rejection.
Every number in this script is the real output of the recorded fixture
snapshot (captured 2026-07-13, 504 common trading days, now frozen) — rerun
the fixture analysis after any backend change and re-verify.

Demo mode is deterministic **including the AI card**: the repo ships real
recorded DeepSeek replies for both demo pairs
(`backend/fixtures/narrative_RCL_CCL.json` and
`backend/fixtures/narrative_ALL_TRV.json`, model `deepseek-v4-flash`,
captured 2026-07-13). Fixture mode replays them labelled **Recorded AI
response — 13 Jul 2026, 15:26 UTC**, needing no network and no key.

---

## The script

### 0:00 – 1:00 — The problem

> "Royal Caribbean and Carnival are two cruise lines that sail through the
> same storms, pay the same fuel prices and fill their ships in the same
> holiday seasons. Their share prices travel together — most of the time.
> Sometimes they drift apart. That drift is either noise that snaps back, or
> news that doesn't.
>
> PairScope answers three questions about any two tickers, in plain English:
> is today's gap between them genuinely unusual, did a fixed trading rule
> actually work on past data after realistic fees, and does recent news
> suggest the gap is temporary or fundamentally explained?
>
> It's an educational research tool. It never claims guaranteed profit, never
> sends an order, and never touches a brokerage.
>
> And here's the spoiler: the tool is honest enough to say *no*. You're about
> to watch it refuse to trade the cruise lines."

### 1:00 – 2:45 — The model (one simple visual, five steps)

Show the spread chart (or the model diagram) and count the steps on your
fingers:

> "The whole model is school-level statistics — a straight line, an average
> and a standard deviation. Five steps:
>
> **One** — we check that their daily returns actually moved together over
> the learning window. Correlation has to be at least 0.60 or we stop right
> there.
>
> **Two** — we draw a line of best fit between their log prices. The slope,
> beta, tells us how much of stock B normally balances stock A.
>
> **Three** — we measure today's distance from that line. We call that
> distance the spread — it's today's error from their normal relationship.
>
> **Four** — we express that distance as a z-score against the previous 60
> days. A z-score of 2 means the gap is about two recent standard deviations
> from normal. It is a ruler for unusualness, not a prediction guarantee. On
> screen we translate it for you: '1.8x the usual drift'.
>
> **Five** — and this is the honest part — we learn the relationship — the
> correlation, the line, everything — on the first 60 percent of dates only,
> then simulate the unchanged rule on the later 40 percent that the fit never
> saw. Signals form at a close; execution happens at the next day's open;
> fees are charged on every leg."

### 2:45 – 6:30 — Live product demo (Demo mode, two beats)

Two pre-validated recorded pairs, one concise route.

#### Beat 1 (2:45 – 4:15) — the fun hook: RCL vs CCL, and the tool says no

1. **Set the scene on the landing page.** Point at **"How it works — the
   30-second version"** — four steps: *Pick two rivals, Spot the gap, Check
   the history, Get a paper trade*:
   > "That strip is the whole product. Let's do it for real."
2. **Enter the pair.** Type `RCL` and `CCL`, leave starting capital at
   10,000, set Data source to **Demo** (the helper text even suggests
   "RCL/CCL (cruise rivals)"). Point out the *Recorded market snapshot*
   banner:
   > "We're demoing on a frozen snapshot of real market data so the result is
   > deterministic — the same provider interface runs live yfinance data."
3. **The Watch verdict.** The banner reads **"Watch — gap not unusual
   enough"** with the one-sentence explanation: *"RCL and CCL pass every
   check, but today's gap (z = +1.80) is below the 2.0 entry threshold, so
   the strategy waits."*
4. **Read the "In plain English" strip aloud, word for word:**
   > "*RCL and CCL usually travel together. Right now their gap is about
   > 1.8× its normal drift — stretched, but not unusual enough to act on. The
   > tool says watch, not trade: every check passed except today's gap being
   > wide enough.*
   >
   > Every result comes with that strip — the machine verdict retold in
   > sentences your grandmother could check."
5. **Walk the four question-cards.** Each card is a question a non-trader
   would actually ask:
   > "**Do they move together?** Pass — 0.85 out of 1.00. Two cruise lines,
   > same storms, same fuel, same holidays — of course they do.
   > **Is the relationship steady?** Pass — balance ratio 1.23, and it barely
   > changed over time.
   > **Is today's gap unusual?** — and here's the honest part — *caution*:
   > **1.8x the usual drift**. Stretched, but our bar is 2.0.
   > **Did the rule work in the past?** Caution again — 5 trades, net +11.2
   > percent after fees, but the app itself calls five trades *limited
   > evidence*, and with no losing trades it prints the profit factor as
   > 'n/a' instead of pretending."
6. **A first taste of the AI.** Glance at the Narrative Lens card — it shows
   **"No obvious news explanation"**, a **Confidence: MEDIUM** chip and the
   **Recorded AI response — 13 Jul 2026, 15:26 UTC** label:
   > "A real DeepSeek reply, recorded and replayed for reliability. It read
   > the recent headlines and found a *shared* story — '*Both companies were
   > part of a larger cruise stock rebound fueled by sector-wide
   > momentum*' — sector-wide, not company-specific. The AI agrees with the
   > maths: nothing special is happening here."
7. **The point of the beat.** Tap the "1.8x the usual drift" card:
   > "Everything about this pair looks great — and the tool still refuses to
   > trade, because today's gap just isn't unusual enough. An honest tool
   > says 'watch' far more often than 'trade'. So what does a green light
   > look like?"

#### Beat 2 (4:15 – 6:30) — the green light: ALL vs TRV

1. **Enter the pair.** Type `ALL` and `TRV` (Allstate and Travelers — two
   big US insurers, same hurricanes, same pricing cycles), still in Demo
   mode. The banner reads **"Candidate setup — sell ALL, buy TRV"** with the
   explanation: *"ALL looks unusually expensive relative to TRV (z = +2.67),
   so the strategy would sell ALL and buy TRV."*
   > "Same four questions — but this time the gap card *passes*: **2.7x the
   > usual drift**, well past our bar of 2. Three passes and one caution: the
   > history card shows **6 trades, net +3.6%** and still wears the
   > *limited evidence* label. Pass, caution or fail — no black box."
2. **"The gap between them" chart.** Point at today's point beyond the
   entry band:
   > "Here's the gap against its ±2 standard-deviation entry bands and the
   > 3.5 stop bands. Today it's 2.7 times the usual drift, so the rule says
   > Allstate is unusually expensive relative to Travelers: sell ALL, buy
   > TRV — as a paper trade."
3. **The proposed paper trade.** Scroll to the trade plan — the labels are
   deliberately plain: **Total position (both sides)**, **Net market bet**,
   **Estimated fees**, **Worst-case estimate vs budget**.
4. **Flip risk profiles.** Switch Conservative → Balanced → Aggressive and
   watch the share counts scale: **SELL 2 ALL / BUY 1 TRV**, then **6 / 3**,
   then **13 / 7**:
   > "Sizing is just: fit both legs inside the money limit using the
   > line-of-best-fit ratio, then scale down until the worst-case estimate
   > fits the risk budget. On Balanced that's sell 6 Allstate, buy 3
   > Travelers — about $2,522 total position, because the worst-case estimate
   > of about $82 has to fit the $100 risk budget. The risk budget is doing
   > the work here, not the exposure cap."
5. **One-line backtest summary.** Point at **"If you'd followed the rule
   (after fees)"**:
   > "On the 40 percent of dates the fit never saw: six completed trades,
   > plus 3.6 percent net after fees, profit factor 1.97, worst drawdown
   > minus 4.4 percent — and the app itself labels six trades as *limited
   > evidence*."
6. **Open the Narrative Lens — and let the AI disagree.** The card leads
   with a red alert — **"Elevated news risk — recent headlines offer a
   possible company-specific explanation for the gap, which may make
   reversion less likely."** — then **"Possible company-specific
   explanation"**, **Confidence: MEDIUM**, a **legal risk** flag and the
   **Recorded AI response — 13 Jul 2026, 15:26 UTC** label:
   > "The model tells us whether the gap is unusual; DeepSeek helps us
   > examine why. And here it *pushes back*: Travelers' headlines are
   > consistently positive — earnings-beat expectations, fair-value
   > upgrades — while Allstate's are mixed, including an Oklahoma lawsuit.
   > That could explain the gap, which would make reversion less likely.
   > The maths proposes the paper trade; the AI hands you the reason to
   > hesitate. Both are on screen, neither is hidden — and the warning never
   > changes the verdict, the backtest or the share counts."
7. **Two cited headlines, max.** Point at a claim and its linked sources —
   e.g. *"Travelers expected to beat earnings estimates"* and *"Allstate
   faces legal risk from Oklahoma lawsuit"*:
   > "Every claim is pinned to a supplied source ID — invented citations get
   > stripped server-side — so you can click through and check the AI's
   > homework. And the card's own footer says it: '*Model:
   > deepseek-v4-flash. The AI reads only the supplied headlines and never
   > changes the trade direction, backtest or share quantities.*'"

   How the AI states work (know them for Q&A):
   - **Demo mode (the judged path)** replays the shipped recorded DeepSeek
     replies deterministically — no network, no key needed. They were
     recorded from the live integration with `cd backend && .venv/bin/python
     scripts/record_fixtures.py --narrative ALL TRV` (requires a real
     `DEEPSEEK_API_KEY`, which lives server-side in the gitignored
     `backend/.env` and is never exposed to the browser).
   - **Live mode** calls DeepSeek for real (card labelled **Live AI**) — a
     fallback flourish, only if tested immediately beforehand.
   - **No key and no recording** — what other users see: **"AI context
     unavailable"**, with the quant analysis fully usable. Graceful
     degradation by design — the quant result never depends on the AI layer.

**Optional beat — the honest rejection (only if ahead of the clock;
otherwise save it for Q&A).** Analyse `KO` / `PEP` in Demo mode:
> "Coke and Pepsi — the textbook pair — and the tool refuses it. Their
> correlation, 0.61, squeaks past the 0.60 bar — but the line of best fit
> between their log prices has a *negative* slope on the learning window, so
> there is no sensible hedge ratio. The verdict says exactly that: 'KO and
> PEP do not qualify as a tradeable pair because the fitted hedge ratio
> (beta = -0.19) is not a positive finite number.' Unsuitable pairs fail
> loudly, with the reason."

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
> share quantities — it's a context layer, not a signal. You just watched it
> disagree with the maths on stage: the quant proposed the Allstate trade
> and the AI flagged elevated news risk right beside it. Both views are
> shown; neither is hidden."

### 7:45 – 9:15 — Why this is credible

> "Why should you trust what you just saw?"

- **Deterministic quant, visibly separate AI.** Arithmetic proposes the paper
  trade; language analysis only flags reasons for caution.
- **No future-data leakage.** Correlation, intercept and beta are all fitted
  on the first 60% of dates only and then frozen; every rolling value uses
  only prior data; tests enforce it.
- **Costs on all four trade legs** — both legs at entry and both at exit.
- **Fixed thresholds, no parameter hunting.** Entry 2.0, exit 0.5, stop 3.5,
  20 days — frozen in one config file and shown in the UI. Nothing was tuned
  to make the demo pass — you just watched the same thresholds tell the
  cruise lines *no*.
- **Automated tests** cover signals, timing, leakage, sizing, sign
  consistency and AI failure modes.
- **Transparent rejection.** Unsuitable pairs fail loudly with the reason —
  we can demo it live: KO/PEP is rejected because its fitted hedge ratio is
  negative, and NVDA/KO because their correlation is −0.23, far below 0.60.
- **Grounded AI output**: structured JSON, Pydantic-validated, every claim
  linked to supplied source IDs — and the demo replays *real* recorded
  DeepSeek replies, honestly labelled **Recorded AI response**, never passed
  off as live.
- **Graceful degradation**: if DeepSeek is down or a user has no key, the
  quant analysis is fully usable and the AI card says so.

### 9:15 – 10:00 — Close

> "PairScope does not promise the future. It turns a trading idea into a
> transparent, testable and risk-sized decision that anyone can inspect.
> Thank you — happy to take questions."

---

## One-page presenter cheat sheet

**The sentence:** PairScope finds two stocks that usually move together,
measures how unusual their current gap is, checks whether a fixed past rule
worked after fees, sizes an understandable two-leg paper trade, and uses AI
to investigate whether news may explain the gap.

**The pitch line:** the numbers tell us whether the gap is unusual; the AI
helps us investigate why.

**The four question-cards (in order):** "Do they move together?" · "Is the
relationship steady?" · "Is today's gap unusual?" · "Did the rule work in
the past?"

| Number | Value |
| --- | --- |
| Correlation threshold | ≥ 0.60 (daily returns, formation window only) |
| Formation / evaluation split | first 60% / final 40% |
| Rolling z-score window | previous 60 days (excluding today) |
| Entry / exit / stop z | 2.0 / 0.5 / 3.5 |
| Max holding | 20 trading days |
| Backtest gate | ≥ 5 trades, net profit > 0, profit factor > 1.0, drawdown ≥ −20% |
| Limited evidence | 5–9 trades |
| Costs | 10 bps per leg per transaction (4 charged legs per round trip) |
| Risk profiles (gross / stress) | Cons. 50%/0.5% · Bal. 75%/1.0% · Agg. 100%/2.0% |
| Stress fallback (no losing trade) | 3% of gross |

**Demo numbers (frozen fixtures, 2y, $10,000 — verify before demo day):**

| Value | RCL/CCL (Beat 1) | ALL/TRV (Beat 2) |
| --- | --- | --- |
| Verdict | **Watch — gap not unusual enough** (`WAIT`) | **Candidate setup — sell ALL, buy TRV** (`SELL_A_BUY_B`) |
| Do they move together? | pass — **0.85 / 1.00** | pass — **0.66 / 1.00** |
| Is the relationship steady? | pass — **balance ratio 1.23** (14% change, 55% leg, 44 crossings) | pass — **balance ratio 0.70** (7% change, 59% leg, 62 crossings) |
| Is today's gap unusual? | **caution — 1.8x the usual drift** (z = +1.80) | pass — **2.7x the usual drift** (z = +2.67, as of 2026-07-13) |
| Did the rule work in the past? | caution — **5 trades, net +11.2%**, PF n/a (no losing trades), DD −2.9%, limited evidence | caution — **6 trades, net +3.6%**, PF **1.97**, DD **−4.4%**, limited evidence |
| Trade plan | none — the tool waits | see sizing rows below |
| Recorded AI reply | **No obvious news explanation** (MEDIUM) — shared story: sector-wide cruise rebound | **Possible company-specific explanation** (MEDIUM) — **Elevated news risk**, flag: legal risk |

**ALL/TRV sizing (whole shares):**

| Profile | Legs | Total position | Worst-case vs budget |
| --- | --- | --- | --- |
| Conservative | SELL 2 ALL / BUY 1 TRV | ≈ $841 | ≈ $27 vs $50 |
| Balanced | SELL 6 ALL / BUY 3 TRV | ≈ $2,522 (est. fees ≈ $5.04) | ≈ $82 vs $100 |
| Aggressive | SELL 13 ALL / BUY 7 TRV | ≈ $5,631 | ≈ $182 vs $200 |

**Rejections:** KO/PEP — correlation 0.61 passes, **beta −0.19 →
UNSUITABLE_PAIR**. NVDA/KO — **correlation −0.23 → UNSUITABLE_PAIR**.

**Directions:** z ≥ +2 → SELL A, BUY B (A expensive). z ≤ −2 → BUY A, SELL B
(A cheap). Otherwise WAIT.

**Sizing in one breath:** use the line-of-best-fit ratio, fit the pair inside
our money limit, then scale it down if the stop could lose more than our risk
allowance.

**Demo route:** RCL + CCL → Demo mode → Watch verdict → read the "In plain
English" strip aloud → 4 question-cards → recorded AI agrees (sector-wide
rebound) → tap "1.8x the usual drift" (honest no) → ALL + TRV → Candidate
setup → "The gap between them" chart → trade plan → flip risk profile (2/1 →
6/3 → 13/7) → one-line backtest → Narrative Lens: recorded AI *disagrees*
(Elevated news risk) → 2 cited headlines (Travelers earnings beat, Allstate
lawsuit). Honest-rejection demo: KO + PEP (backup: NVDA + KO).

**Never say:** "guaranteed", "alpha", "this will make money", "the AI
predicts". **Always say:** "paper trade", "historical screen", "candidate to
re-check", "educational tool".

**If a chart question goes deep:** open the expandable sections — normalised
prices and the after-fees equity view ("If you'd followed the rule (after
fees)") are one click away.

---

## Likely judge questions — with short answers

1. **Why these two stocks?**
   The cruise lines share storms, fuel prices and holiday seasons; the
   insurers share catastrophe and pricing cycles — both relationships are
   plausible before we measure anything. But nothing is hard-coded: any two
   same-currency tickers go through identical checks, and unsuitable pairs
   are rejected with reasons — the textbook Coke/Pepsi pair is rejected on
   this data window because its fitted hedge ratio is negative.

2. **Why isn't correlation enough?**
   Correlation only says their daily moves lined up historically. It says
   nothing about whether today's gap is unusual, whether the relationship is
   stable, or whether acting on gaps ever worked after costs. The demo proves
   it twice: RCL/CCL scores 0.85 and still gets *Watch* because today's gap
   isn't unusual, and KO/PEP squeaks past at 0.61 and is still rejected. It's
   our first filter, never the edge.

3. **What does beta mean?**
   Beta is the slope of the line of best fit between their log prices: the
   relative percentage sensitivity of A to B. We use it to set the notional
   weights of the two legs — it's a money ratio, not a share ratio. The UI
   calls it the balance ratio.

4. **What does a z-score mean?**
   A z-score of 2 means the gap is about two recent standard deviations from
   normal. It is a ruler for unusualness, not a prediction guarantee. The UI
   translates it as "2.7x the usual drift".

5. **How did you avoid looking into the future?**
   Three ways: correlation, intercept and beta are computed only on the first
   60% of dates and then frozen; every rolling mean and standard deviation
   uses only the previous 60 days, excluding today; and a signal formed at a
   close executes at the next day's open. Automated tests assert all three.

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
   profit, and 5–9 trades are explicitly labelled limited evidence: both demo
   pairs passed with six and five trades and wear that caution label on
   screen, and RCL/CCL's profit factor is shown as "n/a — no losing trades"
   rather than pretending five wins prove anything.

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

Demo mode is the internet-free path — it is the *primary* judged demo, so a
network failure changes almost nothing:

1. Everything runs on localhost: backend :8000, frontend :3000. No external
   calls are needed in Demo mode.
2. Both demo pairs replay the frozen recorded market snapshot with Data
   source **Demo** — `RCL` / `CCL` for the Watch beat and `ALL` / `TRV` for
   the Candidate-setup beat — deterministic verdict, story strip, cards,
   charts and sizing, with the *Recorded market snapshot* banner visible.
   Say what it is: a frozen snapshot of real provider data, never
   hand-edited.
3. The Narrative Lens is offline-safe too: the repo ships real recorded
   DeepSeek replies for both demo pairs
   (`backend/fixtures/narrative_RCL_CCL.json`,
   `backend/fixtures/narrative_ALL_TRV.json`, model `deepseek-v4-flash`),
   and Demo mode replays them labelled **Recorded AI response — 13 Jul
   2026, 15:26 UTC** — no network, no key. Only Live mode calls DeepSeek
   for real; offline it degrades gracefully to **AI context unavailable**
   with the quant analysis fully usable.
4. `KO` / `PEP` in Demo mode demos the honest rejection path (negative hedge
   ratio); `NVDA` / `KO` is the blunter rejection (correlation −0.23).
5. If the frontend itself fails, open the backend's `/docs` OpenAPI page and
   execute `POST /api/analyse` with the fixture request — the JSON verdict,
   cards and metrics still tell the story.
6. Last resort: the screenshots in `docs/screenshots/`, all captured on the
   current build against the frozen fixtures:
   - `form.png` — the landing page: the analyse form ("History window",
     "Trading fee (bps per leg)") plus the "How it works — the 30-second
     version" explainer.
   - `verdict-cards.png` — the RCL/CCL Watch verdict with the "In plain
     English" story strip and the four question-cards (Beat 1 in one image).
   - `ai-lens.png` — the recorded AI card for RCL/CCL ("No obvious news
     explanation", Recorded AI response label, cited headlines).
   - `trade-plan.png` — the ALL/TRV proposed paper trade with the plain
     labels (Total position, Net market bet, Estimated fees, Worst-case
     estimate vs budget).
   - `spread-chart.png` — "The gap between them" chart with the entry and
     stop bands.

If live mode is shown at all, test it immediately beforehand and mention that
the same provider interface supports live yfinance data.

---

## Rehearsal checklist (target: under nine minutes)

Run the full script against the clock at least twice. Tick everything:

- [ ] Full run-through timed **under 9:00** (leaves 1+ minute contingency).
- [ ] Timer visible to the co-presenter; hard checkpoints: demo starts by
      2:45, RCL/CCL hands over to ALL/TRV by 4:15, demo ends by 6:30.
- [ ] `make dev` started fresh; backend :8000 and frontend :3000 both up
      **before** the presentation begins.
- [ ] `GET /api/health` returns `ok` (`deepseek_configured` only matters if
      you plan the live-mode flourish — the judged Demo route replays the
      recorded AI replies regardless).
- [ ] RCL/CCL Demo-mode analysis pre-clicked once — Watch verdict ("Watch —
      gap not unusual enough"), story strip, four question-cards
      (pass/pass/caution/caution) and the recorded AI card ("No obvious news
      explanation", sector-wide rebound shared story) all render; the "In
      plain English" strip rehearsed read aloud.
- [ ] ALL/TRV Demo-mode analysis pre-clicked once — verdict ("Candidate setup
      — sell ALL, buy TRV"), four cards (pass/pass/pass/caution), "The gap
      between them" chart, trade plan, and the recorded AI card with the
      **Elevated news risk** alert all render.
- [ ] Risk-profile flip rehearsed: Conservative SELL 2 ALL / BUY 1 TRV,
      Balanced SELL 6 ALL / BUY 3 TRV, Aggressive SELL 13 ALL / BUY 7 TRV —
      and the "risk budget binds, not the cap" line ready.
- [ ] KO/PEP rejection route rehearsed as the honest-failure answer (its
      explanation sentence read aloud once); NVDA/KO as backup.
- [ ] Both recorded AI cards verified to show **Recorded AI response — 13
      Jul 2026, 15:26 UTC** and the `deepseek-v4-flash` footer; if live mode
      will be shown at all, it was tested immediately beforehand.
- [ ] The two cited claims to point at rehearsed: "Travelers expected to
      beat earnings estimates" and "Allstate faces legal risk from Oklahoma
      lawsuit" — both deterministic in Demo mode.
- [ ] Z-score ruler line and closing line memorised verbatim.
- [ ] Cheat-sheet numbers drilled: 0.60, 60/40, 60-day window, 2.0/0.5/3.5,
      20 days, gate of 5 trades / PF > 1 / −20%, 10 bps × 4 legs — plus the
      demo numbers: RCL/CCL corr 0.85, beta 1.23, z +1.80, 5 trades /
      +11.2% / PF n/a / −2.9%; ALL/TRV corr 0.66, beta 0.70, z +2.67,
      6 trades / +3.6% / PF 1.97 / −4.4%.
- [ ] Each presenter can answer all eleven judge questions unprompted.
- [ ] Laptop: notifications off, display sleep off, browser zoom set so the
      verdict, story strip and cards are legible from the back of the room.
- [ ] Backup screenshots in `docs/screenshots/` (`form.png`,
      `verdict-cards.png`, `ai-lens.png`, `trade-plan.png`,
      `spread-chart.png`) spot-checked against the running app once at the
      final rehearsal.
- [ ] Offline drill done once: Wi-Fi disabled, full Demo-mode run still
      works.
