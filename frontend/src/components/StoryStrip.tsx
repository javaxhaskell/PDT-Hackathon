import { Fragment } from "react";

import type { AnalyseResponse } from "@/lib/types";

/** Emphasise a key fact (ticker, figure or action) so it stands out at a glance. */
function B({ children }: { children: React.ReactNode }) {
  return <strong className="font-semibold text-ink">{children}</strong>;
}

/**
 * A plain-English retelling of the result for a non-finance audience.
 * Assembled ONLY from values the backend returned; no quant logic here.
 */
export default function StoryStrip({ result }: { result: AnalyseResponse }) {
  const a = result.request.ticker_a;
  const b = result.request.ticker_b;
  const z = result.signal?.z_score;
  const bt = result.backtest;

  const sentences: React.ReactNode[] = [];

  switch (result.state) {
    case "SELL_A_BUY_B":
    case "BUY_A_SELL_B": {
      const rich = result.state === "SELL_A_BUY_B" ? a : b;
      const cheap = result.state === "SELL_A_BUY_B" ? b : a;
      sentences.push(
        <>
          <B>{a}</B> and <B>{b}</B> usually travel together.
        </>,
      );
      if (z !== undefined) {
        sentences.push(
          <>
            <B>{rich}</B> now looks unusually expensive next to <B>{cheap}</B>:
            the gap is about <B>{Math.abs(z).toFixed(1)}x</B> its normal drift.
          </>,
        );
      }
      if (bt) {
        sentences.push(
          <>
            Betting on this gap closing made{" "}
            <B>{(bt.net_profit * 100).toFixed(1)}%</B> after estimated fees
            across <B>{bt.n_trades} trades</B>
            {bt.limited_evidence
              ? " (a small sample, treat with caution)"
              : ""}
            .
          </>,
        );
      }
      sentences.push(
        <>
          The paper trade:{" "}
          <B>
            sell {rich}, buy {cheap}
          </B>
          , wait for the gap to close.
        </>,
      );
      break;
    }
    case "WAIT": {
      sentences.push(
        <>
          <B>{a}</B> and <B>{b}</B> usually travel together.
        </>,
      );
      if (z !== undefined) {
        sentences.push(
          <>
            Their gap is about <B>{Math.abs(z).toFixed(1)}x</B> its normal
            drift: stretched, but not unusual enough to act on.
          </>,
        );
      }
      sentences.push(
        <>
          <B>Watch, not trade:</B> every check passed except the width of
          today&apos;s gap.
        </>,
      );
      break;
    }
    case "HISTORICAL_SCREEN_FAILED": {
      sentences.push(
        <>
          <B>{a}</B> and <B>{b}</B> move together, but the fixed rule did not
          make money on past data after fees.
        </>,
      );
      sentences.push(
        <>
          <B>No trade suggested:</B> the history has to earn it first.
        </>,
      );
      break;
    }
    case "UNSUITABLE_PAIR": {
      sentences.push(
        <>
          <B>{a}</B> and <B>{b}</B> do not behave like a reliable pair, so the
          tool stops here.
        </>,
      );
      break;
    }
    default:
      return null;
  }

  return (
    <section
      aria-label="Plain-English summary"
      className="rounded-none border border-edge bg-surface px-5 py-4"
    >
      <h3 className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted">
        In plain English
      </h3>
      <p className="mt-2 text-[13px] leading-relaxed text-muted">
        {sentences.map((s, i) => (
          <Fragment key={i}>
            {i > 0 ? " " : ""}
            {s}
          </Fragment>
        ))}
      </p>
    </section>
  );
}
