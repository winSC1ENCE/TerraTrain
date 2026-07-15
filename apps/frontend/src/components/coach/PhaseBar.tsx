"use client";

import type { WorkoutPhase } from "@/lib/types";
import { zoneColor } from "@/lib/zones";

export function PhaseBar({
  phase,
  maxDurationMin,
}: {
  phase: WorkoutPhase;
  maxDurationMin: number;
}) {
  const widthPct = Math.max(8, (phase.duration_min / maxDurationMin) * 100);
  const color = zoneColor(phase.zone);
  const target =
    phase.target_power_pct != null
      ? `${Math.round(phase.target_power_pct)}% FTP`
      : phase.zone.toUpperCase();

  return (
    <div className="flex items-center gap-3">
      <div className="w-28 shrink-0 truncate text-xs text-text-secondary">
        {phase.name}
        {phase.repeat > 1 && (
          <span className="ml-1 text-text-muted">×{phase.repeat}</span>
        )}
      </div>
      <div className="flex-1">
        <div
          className="flex h-6 items-center rounded-md px-2"
          style={{ width: `${widthPct}%`, backgroundColor: color, minWidth: "3.5rem" }}
        >
          {/* Zone code always printed (CVD mitigation for Z4/Z5 colors) */}
          <span className="text-[10px] font-semibold text-black/70">
            {phase.zone.toUpperCase()} · {target}
          </span>
        </div>
      </div>
      <span className="w-14 shrink-0 text-right text-xs tabular-nums text-text-muted">
        {phase.duration_min} min
      </span>
    </div>
  );
}
