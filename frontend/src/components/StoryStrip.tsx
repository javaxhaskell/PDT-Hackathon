import type { AnalyseResponse } from "@/lib/types";

/**
 * A plain-English retelling of the result for a non-finance audience.
 * Assembled ONLY from values the backend returned; no quant logic here.
 */
export default function StoryStrip({ result }: { result: AnalyseResponse }) {
  const a = result.request.ticker_a;
  const b = result.request.ticker_b;
  const z = result.signal?.z_score;
  const bt = result.backtest;

  const sentences: string[] = [];

  switch (result.state) {
    case "SELL_A_BUY_B":
    case "BUY_A_SELL_B": {
      const rich = result.state === "SELL_A_BUY_B" ? a : b;
      const cheap = result.state === "SELL_A_BUY_B" ? b : a;
      sentences.push(`${a} and ${b} usually travel together.`);
      if (z !== undefined) {
        sentences.push(
          `${rich} now looks unusually expensive next to ${cheap}: the gap is about ${Math.abs(z).toFixed(1)}x its normal drift.`,
        );
      }
      if (bt) {
        sentences.push(
          `Betting on this gap closing made ${(bt.net_profit * 100).toFixed(1)}% after estimated fees across ${bt.n_trades} trades${bt.limited_evidence ? " (a small sample, treat with caution)" : ""}.`,
        );
      }
      sentences.push(
        `The paper trade: sell ${rich}, buy ${cheap}, wait for the gap to close.`,
      );
      break;
    }
    case "WAIT": {
      sentences.push(`${a} and ${b} usually travel together.`);
      if (z !== undefined) {
        sentences.push(
          `Their gap is about ${Math.abs(z).toFixed(1)}x its normal drift: stretched, but not unusual enough to act on.`,
        );
      }
      sentences.push(
        "Watch, not trade: every check passed except the width of today's gap.",
      );
      break;
    }
    case "HISTORICAL_SCREEN_FAILED": {
      sentences.push(
        `${a} and ${b} move together, but the fixed rule did not make money on past data after fees.`,
      );
      sentences.push("No trade suggested: the history has to earn it first.");
      break;
    }
    case "UNSUITABLE_PAIR": {
      sentences.push(
        `${a} and ${b} do not behave like a reliable pair, so the tool stops here.`,
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
        {sentences.join(" ")}
      </p>
    </section>
  );
}
