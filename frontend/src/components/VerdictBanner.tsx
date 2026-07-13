import { verdictLabel, verdictTitle, verdictTone } from "@/lib/copy";
import type { FinalState } from "@/lib/types";

const TONE_CHIP = {
  positive: "border-pos/60 text-pos",
  caution: "border-warn/60 text-warn",
  negative: "border-neg/60 text-neg",
} as const;

export default function VerdictBanner({
  state,
  explanation,
  tickerA,
  tickerB,
}: {
  state: FinalState;
  explanation: string;
  tickerA: string;
  tickerB: string;
}) {
  const tone = verdictTone(state);
  return (
    <section
      aria-label="Verdict"
      className="rounded-none border border-edge bg-surface p-6 sm:p-8"
    >
      <p
        className={`inline-block rounded-[2px] border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${TONE_CHIP[tone]}`}
      >
        {verdictLabel(state)}
      </p>
      <h2 className="mt-4 text-balance text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
        {verdictTitle(state, tickerA, tickerB)}
      </h2>
      <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
        {explanation}
      </p>
    </section>
  );
}
