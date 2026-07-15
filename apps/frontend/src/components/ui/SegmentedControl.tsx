"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string; icon?: LucideIcon }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg bg-surface-2 border border-border p-0.5 gap-0.5">
      {options.map((opt) => {
        const active = opt.value === value;
        const Icon = opt.icon;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              active
                ? "bg-surface text-text shadow-sm border border-border-strong"
                : "text-text-muted hover:text-text-secondary"
            )}
          >
            {Icon && <Icon className="h-3.5 w-3.5" />}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
