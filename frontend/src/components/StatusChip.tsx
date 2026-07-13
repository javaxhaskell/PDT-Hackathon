import type { CardStatus } from "@/lib/types";

const STYLES: Record<CardStatus, { label: string; className: string }> = {
  pass: {
    label: "Pass",
    className: "text-pos border-pos/60",
  },
  caution: {
    label: "Caution",
    className: "text-warn border-warn/60",
  },
  fail: {
    label: "Fail",
    className: "text-neg border-neg/60",
  },
};

/** Status tag with a text label; meaning is never colour-only. */
export default function StatusChip({ status }: { status: CardStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center rounded-[2px] border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${s.className}`}
    >
      {s.label}
    </span>
  );
}
