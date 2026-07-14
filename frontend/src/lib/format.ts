/** Pure display formatting. No thresholds, no decisions. */

export function fmtMoney(value: number, currency?: string | null): string {
  if (currency) {
    try {
      return new Intl.NumberFormat("en", {
        style: "currency",
        currency,
        maximumFractionDigits: 2,
      }).format(value);
    } catch {
      // unknown currency code: fall through to a plain number + code
      return `${value.toFixed(2)} ${currency}`;
    }
  }
  return value.toFixed(2);
}

export function fmtPct(value: number, digits = 1, signed = false): string {
  const pct = value * 100;
  const sign = signed && pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)}%`;
}

export function fmtNum(value: number, digits = 2): string {
  return value.toFixed(digits);
}

export function fmtSigned(value: number, digits = 2): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

/** Whole shares render without decimals; fractional shares keep 4 dp. */
export function fmtShares(value: number): string {
  if (Number.isInteger(value)) {
    return value.toFixed(0);
  }
  return value.toFixed(4);
}

/** ISO timestamp -> "13 Jul 2026, 12:00 UTC" (falls back to the raw string). */
export function fmtTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  const text = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(d);
  return `${text} UTC`;
}

/**
 * Turn a machine-style tag into a readable label for display, e.g.
 * "interest_rate_hike_warnings" -> "Interest Rate Hike Warnings" and
 * "geopolitical_tensions" -> "Geopolitical Tensions". Underscores and hyphens
 * become spaces; short all-caps tokens (US, AI, SEC) are kept as acronyms.
 */
export function fmtLabel(raw: string): string {
  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .map((word) =>
      word.length <= 3 && word === word.toUpperCase()
        ? word
        : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase(),
    )
    .join(" ");
}

/** ISO date or timestamp -> "13 Jul 2026". */
export function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}
