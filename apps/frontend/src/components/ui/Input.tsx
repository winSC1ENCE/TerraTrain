"use client";

import { cn } from "@/lib/utils";

interface FieldProps {
  label?: string;
  hint?: string;
  error?: string;
}

const fieldClasses =
  "w-full rounded-lg bg-surface-2 border border-border px-3 py-2 text-sm text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40 transition-colors";

export function Input({
  label,
  hint,
  error,
  className,
  ...props
}: FieldProps & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      {label && (
        <span className="block text-xs font-medium text-text-secondary mb-1.5">
          {label}
        </span>
      )}
      <input className={cn(fieldClasses, error && "border-danger", className)} {...props} />
      {hint && !error && <span className="block text-xs text-text-muted mt-1">{hint}</span>}
      {error && <span className="block text-xs text-danger mt-1">{error}</span>}
    </label>
  );
}

export function Select({
  label,
  hint,
  error,
  className,
  children,
  ...props
}: FieldProps & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="block">
      {label && (
        <span className="block text-xs font-medium text-text-secondary mb-1.5">
          {label}
        </span>
      )}
      <select className={cn(fieldClasses, error && "border-danger", className)} {...props}>
        {children}
      </select>
      {hint && !error && <span className="block text-xs text-text-muted mt-1">{hint}</span>}
      {error && <span className="block text-xs text-danger mt-1">{error}</span>}
    </label>
  );
}

export function Textarea({
  label,
  hint,
  error,
  className,
  ...props
}: FieldProps & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block">
      {label && (
        <span className="block text-xs font-medium text-text-secondary mb-1.5">
          {label}
        </span>
      )}
      <textarea className={cn(fieldClasses, error && "border-danger", className)} {...props} />
      {hint && !error && <span className="block text-xs text-text-muted mt-1">{hint}</span>}
      {error && <span className="block text-xs text-danger mt-1">{error}</span>}
    </label>
  );
}
