"use client";

import {
  CartesianGrid,
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
import type { EquityChart } from "@/lib/types";

export default function EquityView({ chart }: { chart: EquityChart }) {
  const rows = chart.equity
    .filter((p) => p.value !== null && p.value !== undefined)
    .map((p) => ({ date: p.date, equity: p.value as number }))
    .sort((x, y) => (x.date < y.date ? -1 : x.date > y.date ? 1 : 0));

  const renderTooltip = (props: TooltipContentProps) => {
    const { active, payload, label } = props;
    if (!active || !payload || payload.length === 0) return null;
    return (
      <ChartTooltip
        label={String(label ?? "")}
        rows={payload
          .filter((entry) => typeof entry.value === "number")
          .map((entry) => ({
            name: "Equity (after costs)",
            value: entry.value as number,
            color: entry.color,
          }))}
        digits={3}
      />
    );
  };

  return (
    <div
      className="h-[260px] w-full"
      role="img"
      aria-label="Backtest equity chart"
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
            tickFormatter={(v: number) => v.toFixed(2)}
          />
          <Tooltip content={renderTooltip} />
          <ReferenceLine y={1} stroke={CHART_COLORS.grid} />
          <Line
            dataKey="equity"
            name="Equity (after costs)"
            stroke={CHART_COLORS.seriesA}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
