"use client";

import EquityView from "@/components/charts/EquityView";
import NormalisedPricesView from "@/components/charts/NormalisedPricesView";
import SpreadChartView from "@/components/charts/SpreadChartView";
import { fmtPct } from "@/lib/format";
import type { Charts, SignalStats } from "@/lib/types";

export default function ChartsSection({
  charts,
  tickerA,
  tickerB,
  maxDrawdown,
  signal,
}: {
  charts: Charts;
  tickerA: string;
  tickerB: string;
  maxDrawdown?: number | null;
  signal?: SignalStats | null;
}) {
  // Thresholds come from the backend response, never hard-coded here.
  const entryZ = signal?.entry_z;
  const stopZ = signal?.stop_z;
  return (
    <section aria-label="Charts" className="space-y-4">
      <div className="rounded-none border border-edge bg-surface p-5">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
          The gap between them
        </h3>
        <p className="mt-2 text-xs text-faint">
          Distance from the fitted relationship, its rolling mean
          {entryZ !== undefined && stopZ !== undefined
            ? `, entry bands at plus and minus ${entryZ} standard deviations and stop bands at plus and minus ${stopZ}`
            : " and its entry and stop bands"}
          . Dots mark past trade entries and exits.
        </p>
        <div className="mt-3">
          <SpreadChartView
            chart={charts.spread}
            tickerA={tickerA}
            tickerB={tickerB}
            entryZ={entryZ}
            stopZ={stopZ}
          />
        </div>
      </div>

      <details className="group rounded-none border border-edge bg-surface">
        <summary className="cursor-pointer list-none p-5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted transition-colors hover:text-ink">
          <span aria-hidden className="mr-2 inline-block group-open:rotate-90">
            &#9656;
          </span>
          Normalised prices: both stocks start at 100
        </summary>
        <div className="px-5 pb-5">
          <p className="mb-3 text-xs text-faint">
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

      <details className="group rounded-none border border-edge bg-surface">
        <summary className="cursor-pointer list-none p-5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted transition-colors hover:text-ink">
          <span aria-hidden className="mr-2 inline-block group-open:rotate-90">
            &#9656;
          </span>
          Backtested equity curve (after fees)
          {maxDrawdown !== null && maxDrawdown !== undefined && (
            <span className="ml-3 rounded-[2px] border border-neg/60 px-2 py-0.5 font-mono text-xs tabular-nums tracking-normal text-neg">
              Max drawdown {fmtPct(maxDrawdown)}
            </span>
          )}
        </summary>
        <div className="px-5 pb-5">
          <p className="mb-3 text-xs text-faint">
            Growth of one unit of gross exposure through the evaluation period,
            after estimated costs on all four trade legs.
          </p>
          <EquityView chart={charts.equity} />
        </div>
      </details>
    </section>
  );
}
