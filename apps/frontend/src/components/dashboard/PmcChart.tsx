"use client";

import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FitnessPoint } from "@/lib/types";

const CTL = "#3987e5";
const ATL = "#d55181";
const TSB = "#65a30d";

export function PmcChart({ series }: { series: FitnessPoint[] }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-border)" }}
            tickFormatter={(d: string) =>
              new Date(d).toLocaleDateString("de-CH", { day: "2-digit", month: "2-digit" })
            }
            minTickGap={40}
          />
          <YAxis
            tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-surface-2)",
              border: "1px solid var(--color-border-strong)",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--color-text-secondary)" }}
            labelFormatter={(d: string) =>
              new Date(d).toLocaleDateString("de-CH", {
                weekday: "short",
                day: "2-digit",
                month: "2-digit",
              })
            }
          />
          <ReferenceLine y={0} stroke="var(--color-border-strong)" strokeDasharray="4 4" />
          <Area
            type="monotone"
            dataKey="ctl"
            name="CTL"
            stroke={CTL}
            strokeWidth={2}
            fill={CTL}
            fillOpacity={0.12}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="atl"
            name="ATL"
            stroke={ATL}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="tsb"
            name="TSB"
            stroke={TSB}
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="mt-1 flex justify-center gap-4 text-xs text-text-muted">
        <LegendItem color={CTL} label="Fitness (CTL)" />
        <LegendItem color={ATL} label="Ermüdung (ATL)" />
        <LegendItem color={TSB} label="Form (TSB)" />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
