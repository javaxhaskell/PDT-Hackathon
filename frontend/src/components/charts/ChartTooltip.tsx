import { fmtDate } from "@/lib/format";

export interface TooltipRowSpec {
  name: string;
  value: number;
  color?: string;
}

/**
 * Shared tooltip chrome: date first, then exact values, plus an optional
 * extra line (used for trade entry/exit markers).
 */
export default function ChartTooltip({
  label,
  rows,
  digits,
  extra,
}: {
  label?: string;
  rows: TooltipRowSpec[];
  digits: number;
  extra?: string;
}) {
  return (
    <div className="rounded-lg border border-edge bg-surface-deep px-3 py-2 text-xs shadow-xl">
      {label && <p className="font-semibold text-ink">{fmtDate(label)}</p>}
      <ul className="mt-1 space-y-0.5">
        {rows.map((row) => (
          <li key={row.name} className="flex items-center gap-2 text-muted">
            <span
              aria-hidden
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: row.color ?? "var(--muted)" }}
            />
            <span>{row.name}</span>
            <span className="ml-auto pl-3 font-mono text-ink">
              {row.value.toFixed(digits)}
            </span>
          </li>
        ))}
      </ul>
      {extra && <p className="mt-1 font-semibold text-warn-text">{extra}</p>}
    </div>
  );
}
