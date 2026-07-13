"use client";

import EquityView from "@/components/charts/EquityView";
import NormalisedPricesView from "@/components/charts/NormalisedPricesView";
import SpreadChartView from "@/components/charts/SpreadChartView";
import { fmtPct } from "@/lib/format";
import type { Charts } from "@/lib/types";

export default function ChartsSection({
  charts,
  tickerA,
  tickerB,
  maxDrawdown,
}: {
  charts: Charts;
  tickerA: string;
  tickerB: string;
  maxDrawdown?: number | null;
}) {
  return (
    <section aria-label="Charts" className="space-y-4">
      <div className="rounded-xl border border-edge bg-surface p-5">
        <h3 className="text-sm font-semibold text-ink">Spread and signal</h3>
        <p className="mt-1 text-xs text-muted">
          Distance from the fitted relationship, its rolling mean, the entry
          bands at plus and minus 2 standard deviations and the stop bands at
          plus and minus 3.5. Dots mark historical trade entries and exits.
        </p>
        <div className="mt-3">
          <SpreadChartView
            chart={charts.spread}
            tickerA={tickerA}
            tickerB={tickerB}
          />
        </div>
      </div>

      <details className="group rounded-xl border border-edge bg-surface">
        <summary className="cursor-pointer list-none p-5 text-sm font-semibold text-ink transition-colors hover:text-pos-text">
          <span aria-hidden className="mr-2 inline-block group-open:rotate-90">
            &#9656;
          </span>
          Normalised prices — both stocks start at 100
        </summary>
        <div className="px-5 pb-5">
          <p className="mb-3 text-xs text-muted">
            Setting both stocks to 100 on the first common date makes different
            share prices comparable.
          </p>
          <NormalisedPricesView
            chart={charts.normalised_prices}
            tickerA={tickerA}
            tickerB={tickerB}
          />
        </div>
      </details>

      <details className="group rounded-xl border border-edge bg-surface">
        <summary className="cursor-pointer list-none p-5 text-sm font-semibold text-ink transition-colors hover:text-pos-text">
          <span aria-hidden className="mr-2 inline-block group-open:rotate-90">
            &#9656;
          </span>
          Backtest equity (after costs)
          {maxDrawdown !== null && maxDrawdown !== undefined && (
            <span className="ml-3 rounded-full border border-edge bg-surface-deep px-2.5 py-0.5 font-mono text-xs font-semibold text-neg-text">
              Max drawdown {fmtPct(maxDrawdown)}
            </span>
          )}
        </summary>
        <div className="px-5 pb-5">
          <p className="mb-3 text-xs text-muted">
            Growth of one unit of gross exposure through the evaluation period,
            after estimated costs on all four trade legs.
          </p>
          <EquityView chart={charts.equity} />
        </div>
      </details>
    </section>
  );
}
