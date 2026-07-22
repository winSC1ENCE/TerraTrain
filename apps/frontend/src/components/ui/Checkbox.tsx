"use client";

import { cn } from "@/lib/utils";

interface CheckboxProps {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  className?: string;
  disabled?: boolean;
}

export function Checkbox({ label, hint, checked, onChange, className, disabled }: CheckboxProps) {
  return (
    <label className={cn("flex items-start gap-2 cursor-pointer", disabled && "opacity-50 cursor-not-allowed", className)}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-border bg-surface-2 text-accent focus:ring-1 focus:ring-accent/40 focus:outline-none"
      />
      <span>
        <span className="block text-sm text-text">{label}</span>
        {hint && <span className="block text-xs text-text-muted">{hint}</span>}
      </span>
    </label>
  );
}
