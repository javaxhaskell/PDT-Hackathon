"use client";

import { useEffect, useState } from "react";

import { searchSymbols } from "@/lib/api";
import type {
  DataMode,
  Lookback,
  RiskProfile,
  SymbolSearchResult,
} from "@/lib/types";

export interface FormValues {
  tickerA: string;
  tickerB: string;
  startingCapital: string;
  riskProfile: RiskProfile;
  lookback: Lookback;
  wholeShares: boolean;
  costBps: string;
  narrativeOn: boolean;
  dataMode: DataMode;
}

export const DEFAULT_FORM_VALUES: FormValues = {
  tickerA: "",
  tickerB: "",
  startingCapital: "10000",
  riskProfile: "balanced",
  lookback: "2y",
  wholeShares: true,
  costBps: "10",
  narrativeOn: true,
  dataMode: "live",
};

/**
 * Debounced ticker autocomplete. Search failures resolve to an empty list so
 * direct ticker entry always works even when the search endpoint is down.
 */
function useSymbolSearch(query: string): SymbolSearchResult[] {
  const [results, setResults] = useState<SymbolSearchResult[]>([]);
  useEffect(() => {
    const q = query.trim();
    if (q.length === 0) {
      setResults([]);
      return;
    }
    let active = true;
    const timer = setTimeout(() => {
      searchSymbols(q)
        .then((res) => {
          if (active) setResults(res.results);
        })
        .catch(() => {
          if (active) setResults([]);
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query]);
  return results;
}

const labelClass =
  "block text-[10px] font-medium uppercase tracking-[0.14em] text-muted";
const inputClass =
  "mt-1.5 w-full rounded-none border border-edge bg-surface-deep px-3 py-2 text-[13px] text-ink placeholder:text-faint focus:border-ink focus:outline-none";

function TickerField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const results = useSymbolSearch(value);
  const listId = `${id}-options`;
  return (
    <div>
      <label htmlFor={id} className={labelClass}>
        {label}
      </label>
      <input
        id={id}
        list={listId}
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        required
        maxLength={12}
        autoComplete="off"
        spellCheck={false}
        placeholder="e.g. KO"
        className={`${inputClass} font-mono uppercase`}
      />
      <datalist id={listId}>
        {results.map((r) => (
          <option key={r.symbol} value={r.symbol}>
            {r.name}
          </option>
        ))}
      </datalist>
    </div>
  );
}

export default function AnalyseForm({
  values,
  onPatch,
  onRiskProfileChange,
  onSubmit,
  loading,
  currency,
}: {
  values: FormValues;
  onPatch: (patch: Partial<FormValues>) => void;
  onRiskProfileChange: (profile: RiskProfile) => void;
  onSubmit: () => void;
  loading: boolean;
  currency?: string | null;
}) {
  return (
    <form
      aria-label="Analyse a pair"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="rounded-none border border-edge bg-surface p-5 sm:p-6"
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <TickerField
          id="ticker-a"
          label="Ticker A"
          value={values.tickerA}
          onChange={(v) => onPatch({ tickerA: v })}
        />
        <TickerField
          id="ticker-b"
          label="Ticker B"
          value={values.tickerB}
          onChange={(v) => onPatch({ tickerB: v })}
        />
        <div>
          <label htmlFor="capital" className={labelClass}>
            Starting capital{currency ? ` (${currency})` : ""}
          </label>
          <input
            id="capital"
            type="number"
            min={1}
            step="any"
            required
            value={values.startingCapital}
            onChange={(e) => onPatch({ startingCapital: e.target.value })}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="risk" className={labelClass}>
            Risk profile
          </label>
          <select
            id="risk"
            value={values.riskProfile}
            onChange={(e) =>
              onRiskProfileChange(e.target.value as RiskProfile)
            }
            className={inputClass}
          >
            <option value="conservative">Conservative</option>
            <option value="balanced">Balanced</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </div>
        <div>
          <label htmlFor="lookback" className={labelClass}>
            History window
          </label>
          <select
            id="lookback"
            value={values.lookback}
            onChange={(e) => onPatch({ lookback: e.target.value as Lookback })}
            className={inputClass}
          >
            <option value="1y">1 year</option>
            <option value="2y">2 years</option>
            <option value="3y">3 years</option>
          </select>
        </div>
        <div>
          <label htmlFor="cost-bps" className={labelClass}>
            Trading fee (bps per leg)
          </label>
          <input
            id="cost-bps"
            type="number"
            min={0}
            max={200}
            step="any"
            required
            value={values.costBps}
            onChange={(e) => onPatch({ costBps: e.target.value })}
            className={inputClass}
          />
        </div>
        <fieldset>
          <legend className={labelClass}>Share mode</legend>
          <div className="mt-1.5 flex gap-4 rounded-none border border-edge bg-surface-deep px-3 py-2 text-[13px]">
            <label className="flex items-center gap-1.5 text-ink">
              <input
                type="radio"
                name="share-mode"
                checked={values.wholeShares}
                onChange={() => onPatch({ wholeShares: true })}
                className="accent-[var(--foreground)]"
              />
              Whole
            </label>
            <label className="flex items-center gap-1.5 text-ink">
              <input
                type="radio"
                name="share-mode"
                checked={!values.wholeShares}
                onChange={() => onPatch({ wholeShares: false })}
                className="accent-[var(--foreground)]"
              />
              Fractional
            </label>
          </div>
        </fieldset>
        <fieldset>
          <legend className={labelClass}>Data source</legend>
          <div className="mt-1.5 flex gap-4 rounded-none border border-edge bg-surface-deep px-3 py-2 text-[13px]">
            <label className="flex items-center gap-1.5 text-ink">
              <input
                type="radio"
                name="data-mode"
                checked={values.dataMode === "live"}
                onChange={() => onPatch({ dataMode: "live" })}
                className="accent-[var(--foreground)]"
              />
              Live
            </label>
            <label className="flex items-center gap-1.5 text-ink">
              <input
                type="radio"
                name="data-mode"
                checked={values.dataMode === "fixture"}
                onChange={() => onPatch({ dataMode: "fixture" })}
                className="accent-[var(--foreground)]"
              />
              Demo
            </label>
          </div>
          <p className="mt-1.5 text-xs text-faint">
            Live fetches yfinance prices; Demo replays a recorded snapshot.
            Try RCL/CCL (passes, watch), ALL/TRV (trade signal), NVDA/KO
            (unrelated, rejected).
          </p>
        </fieldset>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-edge pt-5">
        <label className="flex items-center gap-2 text-[13px] text-ink">
          <input
            type="checkbox"
            checked={values.narrativeOn}
            onChange={(e) => onPatch({ narrativeOn: e.target.checked })}
            className="h-4 w-4 accent-[var(--foreground)]"
          />
          Narrative Lens (AI news context)
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-none bg-ink px-10 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-background transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Analysing" : "Analyse"}
        </button>
      </div>
    </form>
  );
}
