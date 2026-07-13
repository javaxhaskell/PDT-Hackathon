# PairScope

**PairScope finds two stocks that usually move together, measures how unusual
their current gap is, checks whether a simple past version of the rule worked
after costs, converts the result into an understandable two-leg paper trade,
and uses AI to investigate whether recent news may explain the gap.**

> ⚠️ PairScope is an **educational research tool**. It never claims guaranteed
> profit, never sends an order and never connects to a brokerage. Proposed
> trades are paper examples only, not financial advice.

## How it works (two minutes)

1. **Move together?** Pearson correlation of daily returns must be ≥ 0.60.
2. **Normal relationship.** A line of best fit between log prices (first 60%
   of dates only) gives an intercept and a hedge ratio *beta*.
3. **Spread.** Today's distance from that line.
4. **Z-score.** How many recent standard deviations (previous 60 days) the
   spread is from its recent average. Enter at |z| ≥ 2.0, exit at |z| ≤ 0.5,
   stop at |z| ≥ 3.5, force-exit after 20 trading days.
5. **Historical screen.** The unchanged rule is replayed on the final 40% of
   dates the fit never saw — signals at the close, execution at the next open,
   costs charged on both legs at entry and exit.
6. **Sizing.** Both legs are fitted inside the user's capital and risk budget.

The numbers tell us whether the gap is unusual; the **DeepSeek Narrative
Lens** reads only supplied recent headlines and explains possible reasons why.
It never calculates the trade.

## Quick start

```bash
make setup          # backend venv + frontend npm install
make dev            # backend :8000 + frontend :3000
```

Or separately: `make backend` and `make frontend`.

Open http://localhost:3000, enter two tickers (try **KO / PEP**), pick a risk
profile and press Analyse. Use **fixture mode** for a deterministic offline
demo with recorded real market snapshots.

## Configuration

Copy `.env.example` and fill in what you need. The Narrative Lens needs
`DEEPSEEK_API_KEY`; without it the quant analysis still works and the AI card
shows an unavailable state.

## Tests

```bash
make test           # backend pytest + frontend vitest
```

## Documentation

- [docs/MODEL.md](docs/MODEL.md) — the exact quant model and every threshold
- [docs/API.md](docs/API.md) — API contract
- [docs/PRESENTATION.md](docs/PRESENTATION.md) — ten-minute demo script

## Screenshots

_(added after the UI is built)_

## Assumptions and limitations

- Historical performance does not guarantee future results; relationships break.
- yfinance is an unofficial data source and can be delayed or incomplete.
- Costs are estimated per leg in basis points; bid-ask spreads, borrow fees,
  dividends on shorts, market impact, taxes and corporate events are not fully
  modelled.
- AI summaries can be incomplete or wrong and must be checked against their
  linked sources.

## License

MIT — see [LICENSE](LICENSE).
