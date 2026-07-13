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
    <div className="rounded-lg bg-surface-deep p-3">
      <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </dt>
      <dd className="mt-1 font-mono text-sm font-semibold text-ink">{value}</dd>
      {hint && <dd className="mt-0.5 text-xs text-muted">{hint}</dd>}
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
        className="rounded-xl border border-edge bg-surface p-5"
      >
        <h3 className="text-sm font-semibold text-ink">
          Proposed paper trade
        </h3>
        <p className="mt-2 text-sm text-neg-text">
          No position size proposed
          {sizing.reason ? ` — ${sizing.reason}` : "."}
        </p>
      </section>
    );
  }

  return (
    <section
      aria-label="Trade plan"
      className="rounded-xl border border-edge bg-surface p-5"
    >
      <h3 className="text-sm font-semibold text-ink">
        Proposed paper trade{currency ? ` (${currency})` : ""}
      </h3>

      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {sizing.legs.map((leg) => (
          <li
            key={leg.ticker}
            data-testid={`leg-${leg.ticker}`}
            className={`rounded-lg border p-4 ${
              leg.side === "BUY"
                ? "border-pos/50 bg-pos/10"
                : "border-neg/50 bg-neg/10"
            }`}
          >
            <p
              className={`text-xs font-bold uppercase tracking-widest ${
                leg.side === "BUY" ? "text-pos-text" : "text-neg-text"
              }`}
            >
              {leg.side}
            </p>
            <p className="mt-1 font-mono text-2xl font-bold text-ink">
              {fmtShares(leg.shares)}{" "}
              <span className="text-base font-semibold">
                {leg.ticker} shares
              </span>
            </p>
            <p className="mt-1 text-xs text-muted">
              at {fmtMoney(leg.price, currency)} — notional{" "}
              {fmtMoney(leg.notional, currency)}
            </p>
          </li>
        ))}
      </ul>

      <dl className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label="Gross exposure"
          value={fmtMoney(sizing.gross_exposure, currency)}
          hint={`Allowed: ${fmtMoney(sizing.max_gross_allowed, currency)}`}
        />
        <Stat
          label="Net exposure"
          value={fmtMoney(sizing.net_exposure, currency)}
        />
        <Stat
          label="Estimated cost"
          value={fmtMoney(sizing.estimated_cost, currency)}
          hint="All four legs (entry and exit)"
        />
        <Stat
          label="Stress loss vs budget"
          value={`${fmtMoney(sizing.stress_loss_estimate, currency)} of ${fmtMoney(sizing.risk_budget, currency)}`}
          hint="Worst historical trade applied to this size"
        />
        <Stat
          label="Remaining cash"
          value={fmtMoney(sizing.remaining_cash, currency)}
          hint="Short proceeds are collateral, not spendable cash"
        />
      </dl>

      <p className="mt-3 text-xs leading-relaxed text-muted">
        The stress loss estimate is not a guaranteed maximum loss: prices can
        gap and historical losses can be exceeded.
      </p>
    </section>
  );
}
