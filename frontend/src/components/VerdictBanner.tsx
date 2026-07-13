import { verdictLabel, verdictTitle, verdictTone } from "@/lib/copy";
import type { FinalState } from "@/lib/types";

const TONE_CLASSES = {
  positive: "border-pos/50 bg-pos/10",
  caution: "border-warn/50 bg-warn/10",
  negative: "border-neg/50 bg-neg/10",
} as const;

const TONE_TEXT = {
  positive: "text-pos-text",
  caution: "text-warn-text",
  negative: "text-neg-text",
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
      className={`rounded-2xl border p-6 transition-colors sm:p-8 ${TONE_CLASSES[tone]}`}
    >
      <p
        className={`text-xs font-semibold uppercase tracking-widest ${TONE_TEXT[tone]}`}
      >
        {verdictLabel(state)}
      </p>
      <h2 className="mt-2 text-balance text-3xl font-bold tracking-tight text-ink sm:text-4xl">
        {verdictTitle(state, tickerA, tickerB)}
      </h2>
      <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted">
        {explanation}
      </p>
    </section>
  );
}
