"use client";

import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { tsbLabelKey } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const MIN = -30;
const MAX = 20;

export function FormGauge({ tsb }: { tsb: number }) {
  const t = useT();
  const key = tsbLabelKey(tsb);
  const clamped = Math.max(MIN, Math.min(MAX, tsb));
  const pct = ((clamped - MIN) / (MAX - MIN)) * 100;

  const badgeVariant =
    key === "fresh" || key === "optimal"
      ? ("success" as const)
      : key === "neutral"
        ? ("default" as const)
        : key === "tired"
          ? ("warning" as const)
          : ("danger" as const);

  return (
    <Card className="px-5 py-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-text-muted">{t.dashboard.form}</span>
        <Badge variant={badgeVariant}>{t.dashboard.tsb[key]}</Badge>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-semibold tabular-nums">
          {tsb > 0 ? "+" : ""}
          {tsb.toFixed(1)}
        </span>
      </div>
      {/* Band indicator */}
      <div className="relative mt-3 h-1.5 rounded-full bg-gradient-to-r from-danger via-warning to-success">
        <span
          className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bg bg-text"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-text-muted tabular-nums">
        <span>{MIN}</span>
        <span>0</span>
        <span>+{MAX}</span>
      </div>
    </Card>
  );
}
