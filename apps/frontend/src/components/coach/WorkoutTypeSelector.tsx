"use client";

import { WORKOUT_TYPES } from "@/lib/zones";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function WorkoutTypeSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const t = useT();

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {WORKOUT_TYPES.map(({ value: v, icon: Icon }) => {
        const active = v === value;
        return (
          <button
            key={v}
            type="button"
            onClick={() => onChange(v)}
            className={cn(
              "flex flex-col items-center gap-1.5 rounded-xl border p-3 text-xs font-medium transition-colors",
              active
                ? "border-accent bg-accent/10 text-text"
                : "border-border bg-surface-2/50 text-text-muted hover:border-border-strong hover:text-text-secondary"
            )}
          >
            <Icon
              style={{ width: 18, height: 18 }}
              className={active ? "text-accent" : ""}
            />
            {(t.coach.types as Record<string, string>)[v] ?? v}
          </button>
        );
      })}
    </div>
  );
}
