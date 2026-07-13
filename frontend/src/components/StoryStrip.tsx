import type { AnalyseResponse } from "@/lib/types";

/**
 * A plain-English retelling of the result for a non-finance audience.
 * Assembled ONLY from values the backend returned — no quant logic here.
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
          `Right now ${rich} looks unusually expensive next to ${cheap} — the gap is about ${Math.abs(z).toFixed(1)}× its normal drift.`,
        );
      }
      if (bt) {
        sentences.push(
          `In the recent past, betting that this gap closes made ${(bt.net_profit * 100).toFixed(1)}% after estimated fees across ${bt.n_trades} trades${bt.limited_evidence ? " (a small sample — treat with caution)" : ""}.`,
        );
      }
      sentences.push(
        `So the paper trade: sell ${rich}, buy ${cheap}, and wait for the gap to close.`,
      );
      break;
    }
    case "WAIT": {
      sentences.push(`${a} and ${b} usually travel together.`);
      if (z !== undefined) {
        sentences.push(
          `Right now their gap is about ${Math.abs(z).toFixed(1)}× its normal drift — stretched, but not unusual enough to act on.`,
        );
      }
      sentences.push(
        "The tool says watch, not trade: every check passed except today's gap being wide enough.",
      );
      break;
    }
    case "HISTORICAL_SCREEN_FAILED": {
      sentences.push(
        `${a} and ${b} move together, but replaying the same fixed rule on past data did not make money after fees.`,
      );
      sentences.push("No trade is suggested — the history has to earn it first.");
      break;
    }
    case "UNSUITABLE_PAIR": {
      sentences.push(
        `${a} and ${b} do not behave like a reliable pair, so the tool stops here rather than force a trade.`,
      );
      break;
    }
    default:
      return null;
  }

  return (
    <section
      aria-label="Plain-English summary"
      className="rounded-xl border border-edge bg-surface-deep px-5 py-4"
    >
      <h3 className="text-xs font-semibold uppercase tracking-widest text-muted">
        In plain English
      </h3>
      <p className="mt-2 text-sm leading-relaxed text-ink">
        {sentences.join(" ")}
      </p>
    </section>
  );
}
