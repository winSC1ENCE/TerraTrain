"use client";

import { cn } from "@/lib/utils";

interface SliderProps {
  label?: string;
  hint?: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  labels?: Record<number, string>;
  onChange: (value: number) => void;
  className?: string;
}

export function Slider({
  label,
  hint,
  value,
  min = -2,
  max = 2,
  step = 1,
  labels = {
    "-2": "Sehr niedrig (-2)",
    "-1": "Konservativ (-1)",
    "0": "Normal / Ausgewogen (0)",
    "1": "Intensiv (+1)",
    "2": "Maximal (+2)",
  },
  onChange,
  className,
}: SliderProps) {
  const currentLabel = labels[value] ?? `${value > 0 ? "+" : ""}${value}`;

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between">
        {label && <span className="text-xs font-medium text-text-secondary">{label}</span>}
        <span className="text-xs font-bold text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
          {currentLabel}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-surface-2 rounded-lg appearance-none cursor-pointer accent-accent border border-border"
      />
      <div className="flex justify-between text-[10px] text-text-muted px-0.5">
        <span>Niedrig (-2)</span>
        <span>Normal (0)</span>
        <span>Hoch (+2)</span>
      </div>
      {hint && <p className="text-[11px] text-text-muted mt-0.5">{hint}</p>}
    </div>
  );
}
