"use client";

import { useCallback, useRef, useState } from "react";

import AnalyseForm, {
  DEFAULT_FORM_VALUES,
  type FormValues,
} from "@/components/AnalyseForm";
import ChartsSection from "@/components/ChartsSection";
import EvidenceCardView from "@/components/EvidenceCardView";
import HowItWorks from "@/components/HowItWorks";
import StoryStrip from "@/components/StoryStrip";
import NarrativeCard, {
  type NarrativePanelState,
} from "@/components/NarrativeCard";
import TradePlanPanel from "@/components/TradePlanPanel";
import VerdictBanner from "@/components/VerdictBanner";
import WarningsFooter from "@/components/WarningsFooter";
import { analyse, fetchNarrative } from "@/lib/api";
import { fmtDate, fmtTimestamp } from "@/lib/format";
import type { AnalyseRequest, AnalyseResponse, RiskProfile } from "@/lib/types";

function toRequest(values: FormValues): AnalyseRequest {
  return {
    ticker_a: values.tickerA.trim().toUpperCase(),
    ticker_b: values.tickerB.trim().toUpperCase(),
    starting_capital: Number(values.startingCapital) || 10000,
    risk_profile: values.riskProfile,
    lookback: values.lookback,
    whole_shares: values.wholeShares,
    cost_bps: Number(values.costBps) || 0,
    data_mode: values.dataMode,
  };
}

export default function Home() {
  const [form, setForm] = useState<FormValues>(DEFAULT_FORM_VALUES);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyseResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<NarrativePanelState>({
    status: "off",
  });
  const runIdRef = useRef(0);
  const narrativeKeyRef = useRef<string | null>(null);

  const runAnalyse = useCallback(async (values: FormValues) => {
    const req = toRequest(values);
    if (!req.ticker_a || !req.ticker_b) return;
    const runId = ++runIdRef.current;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await analyse(req);
      if (runId !== runIdRef.current) return;
      setResult(res);
      setLoading(false);

      // The Narrative Lens is fetched separately so the AI card never
      // blocks the quant result. It only depends on the pair + data mode,
      // so a sizing-only change (e.g. risk profile) reuses the last answer.
      if (values.narrativeOn) {
        const key = `${req.ticker_a}|${req.ticker_b}|${req.data_mode}`;
        if (narrativeKeyRef.current !== key) {
          narrativeKeyRef.current = key;
          setNarrative({ status: "loading" });
          fetchNarrative({
            ticker_a: req.ticker_a,
            ticker_b: req.ticker_b,
            data_mode: req.data_mode,
          })
            .then((data) => {
              if (narrativeKeyRef.current === key) {
                setNarrative({ status: "done", data });
              }
            })
            .catch(() => {
              if (narrativeKeyRef.current === key) {
                setNarrative({ status: "error" });
              }
            });
        }
      } else {
        narrativeKeyRef.current = null;
        setNarrative({ status: "off" });
      }
    } catch (e) {
      if (runId !== runIdRef.current) return;
      setLoading(false);
      setResult(null);
      setErrorMsg(
        e instanceof Error ? e.message : "The analysis request failed.",
      );
    }
  }, []);

  const onPatch = useCallback((patch: Partial<FormValues>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  }, []);

  // A risk-profile change re-analyses immediately when results are shown,
  // so share quantities update live during a demo.
  const onRiskProfileChange = useCallback(
    (profile: RiskProfile) => {
      const next = { ...form, riskProfile: profile };
      setForm(next);
      if (result) void runAnalyse(next);
    },
    [form, result, runAnalyse],
  );

  const currency = result?.data?.currency ?? null;
  const displayA = result?.request.ticker_a ?? form.tickerA;
  const displayB = result?.request.ticker_b ?? form.tickerB;

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 border-b border-edge pb-6">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            PairScope
          </h1>
          <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
            Educational research tool. Not financial advice.
          </span>
        </div>
        <p className="mt-3 max-w-3xl text-[13px] leading-relaxed text-muted">
          Two stocks that usually move together sometimes drift apart.
          PairScope checks whether today&apos;s gap is unusual, whether trading
          it worked in the past after fees, and sizes a paper trade to your
          budget; an AI reads recent headlines for context.
        </p>
      </header>

      <AnalyseForm
        values={form}
        onPatch={onPatch}
        onRiskProfileChange={onRiskProfileChange}
        onSubmit={() => void runAnalyse(form)}
        loading={loading}
        currency={currency}
      />

      {errorMsg && (
        <div
          role="alert"
          className="mt-6 rounded-none border border-neg/60 bg-surface p-5"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-neg">
            Analysis failed
          </p>
          <p className="mt-2 text-[13px] text-muted">{errorMsg}</p>
        </div>
      )}

      {result && (
        <main aria-label="Analysis results" className="mt-6 space-y-6">
          {result.data?.is_fixture && (
            <p
              role="status"
              className="rounded-none border border-warn/60 bg-surface-deep px-4 py-3 text-[13px] font-medium text-warn"
            >
              Recorded market snapshot
              {result.data.fixture_captured_at
                ? `. Captured ${fmtTimestamp(result.data.fixture_captured_at)}`
                : ""}
              . Demo data, not live prices.
            </p>
          )}

          <VerdictBanner
            state={result.state}
            explanation={result.explanation}
            tickerA={displayA}
            tickerB={displayB}
          />

          <StoryStrip result={result} />

          {result.data && (
            <p className="font-mono text-[11px] text-faint">
              Data: {result.data.provider} · retrieved{" "}
              {fmtTimestamp(result.data.retrieved_at)} · last market date{" "}
              {fmtDate(result.data.last_market_date)} · {result.data.currency}{" "}
              · {result.data.n_common_observations} common observations ·
              methodology v{result.methodology_version}
            </p>
          )}

          {result.evidence_cards.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {result.evidence_cards.map((card) => (
                <EvidenceCardView key={card.key} card={card} />
              ))}
            </div>
          )}

          <NarrativeCard state={narrative} />

          {result.sizing && (
            <TradePlanPanel sizing={result.sizing} currency={currency} />
          )}

          {result.charts && (
            <ChartsSection
              charts={result.charts}
              tickerA={displayA}
              tickerB={displayB}
              maxDrawdown={result.backtest?.max_drawdown}
              signal={result.signal}
            />
          )}

          <WarningsFooter warnings={result.warnings} />
        </main>
      )}

      {!result && !errorMsg && (
        <div className="mt-6 space-y-6">
          <HowItWorks />
          <div className="rounded-none border border-edge p-8 text-center text-[13px] text-muted">
            Enter two tickers and press Analyse, or switch to Demo and try RCL
            vs CCL.
          </div>
          <WarningsFooter warnings={[]} />
        </div>
      )}
    </div>
  );
}
