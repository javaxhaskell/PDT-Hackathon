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
      className="rounded-xl border border-seriesb/40 bg-gradient-to-br from-surface to-surface-deep p-5"
    >
      <header className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-ink">AI Narrative Lens</h3>
        <span className="rounded-full border border-seriesb/50 bg-seriesb/10 px-2.5 py-0.5 text-xs font-semibold text-seriesb">
          AI-generated
        </span>
      </header>
      <div className="mt-4">{children}</div>
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
      className="text-pos-text underline decoration-pos/50 underline-offset-2 transition-colors hover:text-pos-bright"
    >
      {label}
    </a>
  ) : (
    <span className="text-ink/90">{label}</span>
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
        <p className="text-sm text-muted">
          Narrative Lens is switched off. Turn it on and re-analyse to check
          whether recent headlines might explain the gap.
        </p>
      </Shell>
    );
  }

  if (state.status === "loading") {
    return (
      <Shell>
        <div aria-live="polite" className="space-y-3">
          <p className="text-sm text-muted">Reading recent headlines…</p>
          <div className="h-3 w-2/3 animate-pulse rounded bg-edge" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-edge" />
        </div>
      </Shell>
    );
  }

  if (state.status === "error") {
    return (
      <Shell>
        <p className="text-sm font-semibold text-ink">AI context unavailable</p>
        <p className="mt-1 text-sm text-muted">
          The Narrative Lens could not be reached. The quant analysis above is
          unaffected — it never depends on the AI.
        </p>
      </Shell>
    );
  }

  const data = state.data;

  if (data.ai_status === "unavailable" || data.ai_status === "not_configured") {
    return (
      <Shell>
        <p className="text-sm font-semibold text-ink">AI context unavailable</p>
        <p className="mt-1 text-sm text-muted">
          {data.ai_status === "not_configured"
            ? "No DeepSeek API key is configured on the server."
            : "The AI service did not return a usable answer."}{" "}
          The quant analysis above is unaffected — it never depends on the AI.
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
        <p className="text-sm font-semibold text-ink">
          Insufficient recent news
        </p>
        <p className="mt-1 text-sm text-muted">
          At least one company had fewer than two usable headlines from the
          last 30 days, so no news classification was attempted.
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
            className="rounded-lg border border-neg/60 bg-neg/15 px-3 py-2 text-sm font-bold text-neg-text"
          >
            Elevated news risk — recent headlines offer a possible
            company-specific explanation for the gap, which may make reversion
            less likely.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <p className="text-lg font-bold text-ink">
            {classificationLabel(data.classification)}
          </p>
          {data.confidence && (
            <span className="rounded-full border border-edge bg-surface-deep px-2.5 py-0.5 text-xs font-semibold text-muted">
              Confidence: {data.confidence}
            </span>
          )}
          {data.ai_status === "recorded" && (
            <span className="rounded-full border border-warn/50 bg-warn/15 px-2.5 py-0.5 text-xs font-semibold text-warn-text">
              {aiStatusLabel("recorded")}
              {data.recorded_at ? ` — ${fmtTimestamp(data.recorded_at)}` : ""}
            </span>
          )}
        </div>
        <p className="text-xs text-muted">
          Confidence is the model self-assessment of its reading of the
          headlines. It is not a probability of profit.
        </p>

        {data.explanation && (
          <p className="text-sm leading-relaxed text-ink/90">
            {data.explanation}
          </p>
        )}

        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          {data.summary_a && (
            <div className="rounded-lg bg-surface-deep p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                Company A news
              </dt>
              <dd className="mt-1 text-ink/90">{data.summary_a}</dd>
            </div>
          )}
          {data.summary_b && (
            <div className="rounded-lg bg-surface-deep p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                Company B news
              </dt>
              <dd className="mt-1 text-ink/90">{data.summary_b}</dd>
            </div>
          )}
          {data.shared_story && (
            <div className="rounded-lg bg-surface-deep p-3 sm:col-span-2">
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                Shared story
              </dt>
              <dd className="mt-1 text-ink/90">{data.shared_story}</dd>
            </div>
          )}
        </dl>

        {data.risk_flags.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Risk flags
            </p>
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {data.risk_flags.map((flag) => (
                <li
                  key={flag}
                  className="rounded-full border border-warn/40 bg-warn/10 px-2.5 py-0.5 text-xs text-warn-text"
                >
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        )}

        {data.evidence.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Evidence and cited headlines
            </p>
            <ul className="mt-2 space-y-3">
              {data.evidence.map((claim) => (
                <li
                  key={claim.claim}
                  className="rounded-lg border border-edge bg-surface-deep p-3"
                >
                  <p className="text-sm text-ink/90">{claim.claim}</p>
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
            <summary className="cursor-pointer font-semibold">
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

        <p className="text-xs text-muted">
          {data.model ? `Model: ${data.model}. ` : ""}The AI reads only the
          supplied headlines and never changes the trade direction, backtest or
          share quantities.
        </p>
      </div>
    </Shell>
  );
}
