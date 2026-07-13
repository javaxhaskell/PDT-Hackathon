"use client";

import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipContentProps } from "recharts";

import ChartTooltip from "@/components/charts/ChartTooltip";
import {
  AXIS_TICK,
  CHART_COLORS,
  shortDate,
} from "@/components/charts/chartTheme";
import { directionCopy } from "@/lib/copy";
import { fmtSigned } from "@/lib/format";
import type { SpreadChart, SpreadMarker } from "@/lib/types";

interface Row {
  date: string;
  spread?: number;
  mean?: number;
  upperEntry?: number;
  lowerEntry?: number;
  upperStop?: number;
  lowerStop?: number;
  entryMarker?: number;
  exitMarker?: number;
  markerInfo?: SpreadMarker;
}

function buildRows(chart: SpreadChart): Row[] {
  const byDate = new Map<string, Row>();
  const row = (date: string): Row => {
    let r = byDate.get(date);
    if (!r) {
      r = { date };
      byDate.set(date, r);
    }
    return r;
  };
  const assign = (
    points: { date: string; value?: number | null }[],
    key: keyof Omit<Row, "date" | "markerInfo">,
  ) => {
    for (const p of points) {
      if (p.value !== null && p.value !== undefined) {
        row(p.date)[key] = p.value;
      }
    }
  };
  assign(chart.spread, "spread");
  assign(chart.rolling_mean, "mean");
  assign(chart.upper_entry, "upperEntry");
  assign(chart.lower_entry, "lowerEntry");
  assign(chart.upper_stop, "upperStop");
  assign(chart.lower_stop, "lowerStop");
  for (const marker of chart.markers) {
    const r = byDate.get(marker.date);
    if (!r || r.spread === undefined) continue;
    if (marker.kind === "entry") r.entryMarker = r.spread;
    else r.exitMarker = r.spread;
    r.markerInfo = marker;
  }
  return Array.from(byDate.values()).sort((a, b) =>
    a.date < b.date ? -1 : a.date > b.date ? 1 : 0,
  );
}

function MarkerDot(props: unknown) {
  const { cx, cy, fill } = props as {
    cx?: number;
    cy?: number;
    fill?: string;
  };
  if (cx === undefined || cy === undefined) return <g />;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={4}
      fill={fill}
      stroke={CHART_COLORS.surface}
      strokeWidth={1}
    />
  );
}

export default function SpreadChartView({
  chart,
  tickerA,
  tickerB,
  entryZ,
  stopZ,
}: {
  chart: SpreadChart;
  tickerA: string;
  tickerB: string;
  entryZ?: number;
  stopZ?: number;
}) {
  // Band labels use the server-supplied thresholds when available.
  const entryLabel = entryZ !== undefined ? String(entryZ) : "entry";
  const stopLabel = stopZ !== undefined ? String(stopZ) : "stop";
  const rows = buildRows(chart);
  const boundary =
    rows.find((r) => r.date >= chart.formation_end)?.date ?? rows[0]?.date;

  const renderTooltip = (props: TooltipContentProps) => {
    const { active, payload, label } = props;
    if (!active || !payload || payload.length === 0) return null;
    const rowData = payload[0]?.payload as Row | undefined;
    const seen = new Set<string>();
    const rowsToShow = payload
      .filter((entry) => {
        const key = String(entry.dataKey ?? entry.name);
        if (key === "entryMarker" || key === "exitMarker") return false;
        if (typeof entry.value !== "number") return false;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((entry) => ({
        name: String(entry.name),
        value: entry.value as number,
        color: entry.color,
      }));
    const marker = rowData?.markerInfo;
    const extra = marker
      ? `${marker.kind === "entry" ? "Trade entry" : "Trade exit"}: ${directionCopy(marker.direction, tickerA, tickerB)} (z = ${fmtSigned(marker.z)})`
      : undefined;
    return (
      <ChartTooltip
        label={String(label ?? rowData?.date ?? "")}
        rows={rowsToShow}
        digits={4}
        extra={extra}
      />
    );
  };

  return (
    <div className="h-[340px] w-full" role="img" aria-label="Spread chart">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={rows}
          margin={{ top: 12, right: 16, bottom: 4, left: 4 }}
        >
          <CartesianGrid
            stroke={CHART_COLORS.grid}
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: CHART_COLORS.grid }}
            minTickGap={48}
            tickFormatter={shortDate}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={64}
            tickFormatter={(v: number) => v.toFixed(3)}
          />
          <Tooltip content={renderTooltip} />
          <Legend
            formatter={(value) => (
              <span style={{ color: CHART_COLORS.legend, fontSize: 11 }}>
                {value}
              </span>
            )}
          />
          <Line
            dataKey="upperStop"
            name={`Stop band (+${stopLabel} sd)`}
            stroke={CHART_COLORS.stopBand}
            strokeOpacity={0.5}
            strokeWidth={1}
            strokeDasharray="2 4"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="lowerStop"
            name={`Stop band (-${stopLabel} sd)`}
            stroke={CHART_COLORS.stopBand}
            strokeOpacity={0.5}
            strokeWidth={1}
            strokeDasharray="2 4"
            dot={false}
            legendType="none"
            isAnimationActive={false}
          />
          <Line
            dataKey="upperEntry"
            name={`Entry band (+${entryLabel} sd)`}
            stroke={CHART_COLORS.entryBand}
            strokeOpacity={0.6}
            strokeWidth={1}
            strokeDasharray="6 4"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="lowerEntry"
            name={`Entry band (-${entryLabel} sd)`}
            stroke={CHART_COLORS.entryBand}
            strokeOpacity={0.6}
            strokeWidth={1}
            strokeDasharray="6 4"
            dot={false}
            legendType="none"
            isAnimationActive={false}
          />
          <Line
            dataKey="mean"
            name="Rolling mean"
            stroke={CHART_COLORS.mean}
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="spread"
            name="Spread"
            stroke={CHART_COLORS.seriesA}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Scatter
            dataKey="entryMarker"
            name="Trade entry"
            fill={CHART_COLORS.markerEntry}
            shape={<MarkerDot />}
            isAnimationActive={false}
          />
          <Scatter
            dataKey="exitMarker"
            name="Trade exit"
            fill={CHART_COLORS.markerExit}
            shape={<MarkerDot />}
            isAnimationActive={false}
          />
          {boundary && (
            <ReferenceLine
              x={boundary}
              stroke={CHART_COLORS.reference}
              strokeDasharray="4 2"
              label={{
                value: "fit ends / test begins",
                position: "insideTopLeft",
                fill: CHART_COLORS.tick,
                fontSize: 10,
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
