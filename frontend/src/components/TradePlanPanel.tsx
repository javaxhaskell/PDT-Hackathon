import { fmtMoney, fmtShares } from "@/lib/format";
import type { SizingResult } from "@/lib/types";

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="border-t border-edge pt-2">
      <dt className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
        {label}
      </dt>
      <dd className="mt-1 font-mono text-sm font-semibold tabular-nums text-ink">
        {value}
      </dd>
      {hint && <dd className="mt-0.5 text-[11px] text-faint">{hint}</dd>}
    </div>
  );
}

export default function TradePlanPanel({
  sizing,
  currency,
}: {
  sizing: SizingResult;
  currency?: string | null;
}) {
  if (!sizing.sized) {
    return (
      <section
        aria-label="Trade plan"
        className="rounded-none border border-edge bg-surface p-5"
      >
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
          Proposed paper trade
        </h3>
        <p className="mt-3 text-[13px] text-neg">
          No position size proposed
          {sizing.reason ? `: ${sizing.reason}` : "."}
        </p>
      </section>
    );
  }

  return (
    <section
      aria-label="Trade plan"
      className="rounded-none border border-edge bg-surface p-5"
    >
      <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
        Proposed paper trade{currency ? ` (${currency})` : ""}
      </h3>

      <ul className="mt-4 grid gap-4 sm:grid-cols-2">
        {sizing.legs.map((leg) => (
          <li
            key={leg.ticker}
            data-testid={`leg-${leg.ticker}`}
            className="rounded-none border border-edge bg-surface-deep p-4"
          >
            <p
              className={`inline-block rounded-[2px] border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] ${
                leg.side === "BUY"
                  ? "border-pos/60 text-pos"
                  : "border-neg/60 text-neg"
              }`}
            >
              {leg.side}
            </p>
            <p className="mt-2 font-mono text-3xl font-semibold tabular-nums text-ink">
              {fmtShares(leg.shares)}{" "}
              <span className="text-base font-medium">
                {leg.ticker} shares
              </span>
            </p>
            <p className="mt-1 font-mono text-xs text-muted">
              at {fmtMoney(leg.price, currency)}, notional{" "}
              {fmtMoney(leg.notional, currency)}
            </p>
          </li>
        ))}
      </ul>

      <dl className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat
          label="Total position (both sides)"
          value={fmtMoney(sizing.gross_exposure, currency)}
          hint={`Allowed: ${fmtMoney(sizing.max_gross_allowed, currency)}`}
        />
        <Stat
          label="Net market bet"
          value={fmtMoney(sizing.net_exposure, currency)}
        />
        <Stat
          label="Estimated fees"
          value={fmtMoney(sizing.estimated_cost, currency)}
          hint="All four legs, entry and estimated exit"
        />
        <Stat
          label="Worst-case estimate vs budget"
          value={`${fmtMoney(sizing.stress_loss_estimate, currency)} of ${fmtMoney(sizing.risk_budget, currency)}`}
          hint="Worst past trade at this size"
        />
        <Stat
          label="Remaining cash"
          value={fmtMoney(sizing.remaining_cash, currency)}
          hint="Short proceeds are collateral, not cash"
        />
      </dl>

      <p className="mt-4 text-xs leading-relaxed text-muted">
        The stress loss estimate is not a guaranteed maximum loss: prices can
        gap and historical losses can be exceeded.
      </p>
    </section>
  );
}
