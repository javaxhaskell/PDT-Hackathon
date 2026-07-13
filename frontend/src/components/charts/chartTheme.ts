/** Shared visual constants for the Recharts views. */

export const CHART_COLORS = {
  // Monochrome-first: white data line, grey mean/second series; semantic
  // colour only on entry/stop bands and trade markers.
  seriesA: "#e8eaed", // spread line / ticker A / equity
  seriesB: "#98a0a8", // ticker B (muted grey)
  mean: "#656c74", // rolling mean, dashed
  entryBand: "#c29234", // amber: entry bands
  stopBand: "#d95f52", // coral: stop bands
  markerEntry: "#d95f52", // trade entry markers
  markerExit: "#2fb5a3", // trade exit markers
  surface: "#0d1016",
  grid: "rgba(255, 255, 255, 0.05)",
  reference: "rgba(255, 255, 255, 0.25)", // faint white reference lines
  tick: "#656c74",
  legend: "#98a0a8",
} as const;

export const AXIS_TICK = { fill: CHART_COLORS.tick, fontSize: 10 } as const;

export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  }).format(d);
}
