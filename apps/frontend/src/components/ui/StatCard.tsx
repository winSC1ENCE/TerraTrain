import type { LucideIcon } from "lucide-react";
import { Card } from "./Card";

export function StatCard({
  label,
  value,
  unit,
  sub,
  accent,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  unit?: string;
  sub?: React.ReactNode;
  accent?: string;
  icon?: LucideIcon;
}) {
  return (
    <Card className="px-5 py-4">
      <div className="flex items-center gap-1.5 text-xs text-text-muted mb-2">
        {accent && (
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: accent }}
          />
        )}
        {Icon && <Icon className="h-3.5 w-3.5" />}
        <span>{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-semibold tabular-nums text-text">{value}</span>
        {unit && <span className="text-sm text-text-muted">{unit}</span>}
      </div>
      {sub && <div className="text-xs text-text-muted mt-1">{sub}</div>}
    </Card>
  );
}
