import { aiStatusLabel, classificationLabel } from "@/lib/copy";
import { fmtTimestamp } from "@/lib/format";
import type { NarrativeResponse, NewsItem } from "@/lib/types";

export type NarrativePanelState =
  | { status: "off" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "done"; data: NarrativeResponse };

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <section
      aria-label="AI Narrative Lens"
      className="rounded-none border border-edge bg-surface p-5"
    >
      <header className="flex flex-wrap items-center gap-2">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
          AI Narrative Lens
        </h3>
        <span className="rounded-[2px] border border-edge px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
          AI-generated
        </span>
      </header>
      <div className="mt-4 border-t border-edge pt-4">{children}</div>
    </section>
  );
}

function SourceLink({ item }: { item: NewsItem }) {
  const label = `${item.headline} (${item.source}, ${item.ticker})`;
  return item.url ? (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-ink underline decoration-edge underline-offset-2 transition-colors hover:decoration-muted"
    >
      {label}
    </a>
  ) : (
    <span className="text-ink">{label}</span>
  );
}

export default function NarrativeCard({
  state,
}: {
  state: NarrativePanelState;
}) {
  if (state.status === "off") {
    return (
      <Shell>
        <p className="text-[13px] text-muted">
          Narrative Lens is off. Turn it on and re-analyse for headline
          context.
        </p>
      </Shell>
    );
  }

  if (state.status === "loading") {
    return (
      <Shell>
        <div aria-live="polite" className="space-y-3">
          <p className="text-[13px] text-muted">Reading recent headlines</p>
          <div className="h-3 w-2/3 animate-pulse rounded-none bg-white/5" />
          <div className="h-3 w-1/2 animate-pulse rounded-none bg-white/5" />
        </div>
      </Shell>
    );
  }

  if (state.status === "error") {
    return (
      <Shell>
        <p className="text-[13px] font-medium text-ink">
          AI context unavailable
        </p>
        <p className="mt-1 text-[13px] text-muted">
          The Narrative Lens could not be reached. The quant analysis above is
          unaffected.
        </p>
      </Shell>
    );
  }

  const data = state.data;

  if (data.ai_status === "unavailable" || data.ai_status === "not_configured") {
    return (
      <Shell>
        <p className="text-[13px] font-medium text-ink">
          AI context unavailable
        </p>
        <p className="mt-1 text-[13px] text-muted">
          {data.ai_status === "not_configured"
            ? "No DeepSeek API key is configured on the server."
            : "The AI service did not return a usable answer."}{" "}
          The quant analysis above is unaffected.
        </p>
      </Shell>
    );
  }

  if (
    data.ai_status === "insufficient_news" ||
    data.classification === "INSUFFICIENT_NEWS"
  ) {
    return (
      <Shell>
        <p className="text-[13px] font-medium text-ink">
          Insufficient recent news
        </p>
        <p className="mt-1 text-[13px] text-muted">
          At least one company had fewer than two usable headlines in the last
          30 days; no classification was attempted.
        </p>
      </Shell>
    );
  }

  const citedItems = (ids: string[]) =>
    data.news_items.filter((n) => ids.includes(n.source_id));

  return (
    <Shell>
      <div className="space-y-4">
        {data.elevated_news_risk && (
          <p
            role="alert"
            className="rounded-none border border-neg/60 px-3 py-2 text-[13px] font-medium text-neg"
          >
            Elevated news risk: headlines offer a possible company-specific
            explanation, which may make reversion less likely.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <p className="text-lg font-semibold text-ink">
            {classificationLabel(data.classification)}
          </p>
          {data.confidence && (
            <span className="rounded-[2px] border border-edge px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
              Confidence: {data.confidence}
            </span>
          )}
          {data.ai_status === "recorded" && (
            <span className="rounded-[2px] border border-warn/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-warn">
              {aiStatusLabel("recorded")}
              {data.recorded_at ? `, ${fmtTimestamp(data.recorded_at)}` : ""}
            </span>
          )}
        </div>
        <p className="text-xs text-faint">
          Confidence is the model&apos;s self-assessment of its reading, not a
          probability of profit.
        </p>

        {data.explanation && (
          <p className="text-[13px] leading-relaxed text-ink">
            {data.explanation}
          </p>
        )}

        <dl className="grid gap-3 text-[13px] sm:grid-cols-2">
          {data.summary_a && (
            <div className="rounded-none border border-edge bg-surface-deep p-3">
              <dt className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
                Company A news
              </dt>
              <dd className="mt-1 text-muted">{data.summary_a}</dd>
            </div>
          )}
          {data.summary_b && (
            <div className="rounded-none border border-edge bg-surface-deep p-3">
              <dt className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
                Company B news
              </dt>
              <dd className="mt-1 text-muted">{data.summary_b}</dd>
            </div>
          )}
          {data.shared_story && (
            <div className="rounded-none border border-edge bg-surface-deep p-3 sm:col-span-2">
              <dt className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
                Shared story
              </dt>
              <dd className="mt-1 text-muted">{data.shared_story}</dd>
            </div>
          )}
        </dl>

        {data.risk_flags.length > 0 && (
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
              Risk flags
            </p>
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {data.risk_flags.map((flag) => (
                <li
                  key={flag}
                  className="rounded-[2px] border border-warn/60 px-2 py-0.5 text-xs text-warn"
                >
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        )}

        {data.evidence.length > 0 && (
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
              Evidence and cited headlines
            </p>
            <ul className="mt-2 space-y-3">
              {data.evidence.map((claim) => (
                <li
                  key={claim.claim}
                  className="rounded-none border border-edge bg-surface-deep p-3"
                >
                  <p className="text-[13px] text-ink">{claim.claim}</p>
                  <ul className="mt-2 space-y-1 text-xs">
                    {citedItems(claim.source_ids).map((item) => (
                      <li key={item.source_id}>
                        <SourceLink item={item} />
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        )}

        {data.news_items.length > 0 && (
          <details className="text-xs text-muted">
            <summary className="cursor-pointer font-medium">
              All headlines supplied to the model ({data.news_items.length})
            </summary>
            <ul className="mt-2 space-y-1">
              {data.news_items.map((item) => (
                <li key={item.source_id}>
                  <SourceLink item={item} />
                </li>
              ))}
            </ul>
          </details>
        )}

        <p className="border-t border-edge pt-3 text-xs text-faint">
          {data.model ? `Model: ${data.model}. ` : ""}The AI reads only the
          supplied headlines and never changes the trade direction, backtest or
          share quantities.
        </p>
      </div>
    </Shell>
  );
}
