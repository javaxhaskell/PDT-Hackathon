"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
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
import type { NormalisedPricesChart } from "@/lib/types";

interface Row {
  date: string;
  a?: number;
  b?: number;
}

function buildRows(chart: NormalisedPricesChart): Row[] {
  const byDate = new Map<string, Row>();
  const row = (date: string): Row => {
    let r = byDate.get(date);
    if (!r) {
      r = { date };
      byDate.set(date, r);
    }
    return r;
  };
  for (const p of chart.a) {
    if (p.value !== null && p.value !== undefined) row(p.date).a = p.value;
  }
  for (const p of chart.b) {
    if (p.value !== null && p.value !== undefined) row(p.date).b = p.value;
  }
  return Array.from(byDate.values()).sort((x, y) =>
    x.date < y.date ? -1 : x.date > y.date ? 1 : 0,
  );
}

export default function NormalisedPricesView({
  chart,
  tickerA,
  tickerB,
}: {
  chart: NormalisedPricesChart;
  tickerA: string;
  tickerB: string;
}) {
  const rows = buildRows(chart);

  const renderTooltip = (props: TooltipContentProps) => {
    const { active, payload, label } = props;
    if (!active || !payload || payload.length === 0) return null;
    return (
      <ChartTooltip
        label={String(label ?? "")}
        rows={payload
          .filter((entry) => typeof entry.value === "number")
          .map((entry) => ({
            name: String(entry.name),
            value: entry.value as number,
            color: entry.color,
          }))}
        digits={2}
      />
    );
  };

  return (
    <div
      className="h-[280px] w-full"
      role="img"
      aria-label="Normalised prices chart"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
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
            width={56}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => v.toFixed(0)}
          />
          <Tooltip content={renderTooltip} />
          <Legend
            formatter={(value) => (
              <span style={{ color: CHART_COLORS.tick, fontSize: 12 }}>
                {value}
              </span>
            )}
          />
          <ReferenceLine y={100} stroke={CHART_COLORS.grid} />
          <Line
            dataKey="a"
            name={tickerA}
            stroke={CHART_COLORS.seriesA}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="b"
            name={tickerB}
            stroke={CHART_COLORS.seriesB}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
