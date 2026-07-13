import type { CardStatus } from "@/lib/types";

const STYLES: Record<CardStatus, { label: string; className: string }> = {
  pass: {
    label: "Pass",
    className: "bg-pos/15 text-pos-text border-pos/40",
  },
  caution: {
    label: "Caution",
    className: "bg-warn/15 text-warn-text border-warn/40",
  },
  fail: {
    label: "Fail",
    className: "bg-neg/15 text-neg-text border-neg/40",
  },
};

/** Status chip with a text label — meaning is never colour-only. */
export default function StatusChip({ status }: { status: CardStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${s.className}`}
    >
      {s.label}
    </span>
  );
}
