/**
 * Display copy for backend states. Pure mapping — the backend decides the
 * state; this file only turns machine-readable enums into words.
 */

import type {
  AiStatus,
  Direction,
  FinalState,
  NarrativeClassification,
} from "@/lib/types";

export type VerdictTone = "positive" | "caution" | "negative";

export function verdictTitle(
  state: FinalState,
  tickerA: string,
  tickerB: string,
): string {
  switch (state) {
    case "BUY_A_SELL_B":
      return `Candidate setup — buy ${tickerA}, sell ${tickerB}`;
    case "SELL_A_BUY_B":
      return `Candidate setup — sell ${tickerA}, buy ${tickerB}`;
    case "WAIT":
      return "Watch — gap not unusual enough";
    case "HISTORICAL_SCREEN_FAILED":
      return "Historical screen failed";
    case "UNSUITABLE_PAIR":
      return "Not a suitable pair";
    case "INSUFFICIENT_DATA":
      return "Insufficient data";
    case "PROVIDER_ERROR":
      return "Data provider error";
  }
}

export function verdictTone(state: FinalState): VerdictTone {
  switch (state) {
    case "BUY_A_SELL_B":
    case "SELL_A_BUY_B":
      return "positive";
    case "WAIT":
      return "caution";
    default:
      return "negative";
  }
}

export function verdictLabel(state: FinalState): string {
  switch (state) {
    case "BUY_A_SELL_B":
    case "SELL_A_BUY_B":
      return "Candidate setup";
    case "WAIT":
      return "Watch";
    default:
      return "No setup";
  }
}

export function directionCopy(
  direction: Direction,
  tickerA: string,
  tickerB: string,
): string {
  return direction === "SELL_A_BUY_B"
    ? `sell ${tickerA}, buy ${tickerB}`
    : `buy ${tickerA}, sell ${tickerB}`;
}

export function classificationLabel(c: NarrativeClassification): string {
  switch (c) {
    case "NO_OBVIOUS_NEWS_EXPLANATION":
      return "No obvious news explanation";
    case "POSSIBLE_COMPANY_SPECIFIC_EXPLANATION":
      return "Possible company-specific explanation";
    case "MIXED":
      return "Mixed news picture";
    case "INSUFFICIENT_NEWS":
      return "Insufficient recent news";
    case "AI_UNAVAILABLE":
      return "AI context unavailable";
  }
}

export function aiStatusLabel(status: AiStatus): string {
  switch (status) {
    case "ok":
      return "Live AI";
    case "recorded":
      return "Recorded AI response";
    case "insufficient_news":
      return "Insufficient news";
    case "not_configured":
      return "AI not configured";
    case "unavailable":
      return "AI context unavailable";
  }
}

export const EDUCATIONAL_DISCLAIMER =
  "PairScope is an educational research tool. Proposed trades are paper " +
  "examples only, not financial advice, and nothing here guarantees profit. " +
  "It never sends orders and never connects to a brokerage.";

export const STANDING_WARNINGS: string[] = [
  "Historical performance does not guarantee future results.",
  "Correlation and price relationships can break without warning.",
  "yfinance is an unofficial data source and can be delayed or incomplete.",
  "Cost estimates exclude bid-ask spreads, borrow availability and fees, dividends on short positions, market impact, taxes and corporate events.",
  "AI summaries can be incomplete or wrong and must be checked against their linked sources.",
];
