/** Shared visual constants for the Recharts views. */

export const CHART_COLORS = {
  // Validated for CVD separation and >=3:1 contrast on the dark surface.
  seriesA: "#0fa393", // teal — spread line / ticker A / equity
  seriesB: "#9085e9", // violet — ticker B
  mean: "#96a3ba", // muted grey — rolling mean
  entryBand: "#c98500", // amber — caution / entry bands
  stopBand: "#e66767", // coral — risk / stop bands
  surface: "#0e1626",
  grid: "#1e2942",
  tick: "#96a3ba",
} as const;

export const AXIS_TICK = { fill: CHART_COLORS.tick, fontSize: 11 } as const;

export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  }).format(d);
}
