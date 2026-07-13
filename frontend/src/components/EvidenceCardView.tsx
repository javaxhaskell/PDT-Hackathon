import InfoTip from "@/components/InfoTip";
import StatusChip from "@/components/StatusChip";
import type { EvidenceCard } from "@/lib/types";

export default function EvidenceCardView({ card }: { card: EvidenceCard }) {
  return (
    <article
      aria-label={card.title}
      className="flex flex-col gap-3 rounded-none border border-edge bg-surface p-4"
    >
      <header className="flex items-start justify-between gap-2">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
          {card.title}
        </h3>
        <StatusChip status={card.status} />
      </header>
      <p className="font-mono text-2xl font-semibold tabular-nums text-ink">
        {card.headline_value}
      </p>
      <ul className="space-y-1 font-mono text-xs leading-relaxed text-muted">
        {card.detail_lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="text-[13px] leading-relaxed text-muted">
        {card.plain_english}
      </p>
      <footer className="mt-auto flex justify-end border-t border-edge pt-3">
        <InfoTip text={card.how_this_works} />
      </footer>
    </article>
  );
}
