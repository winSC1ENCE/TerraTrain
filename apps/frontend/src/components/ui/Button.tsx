"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const button = cva(
  "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-2 focus-visible:outline-accent",
  {
    variants: {
      variant: {
        primary: "bg-accent text-on-accent hover:bg-accent-hover",
        secondary:
          "bg-surface-2 text-text border border-border hover:border-border-strong",
        ghost: "text-text-secondary hover:text-text hover:bg-surface-2",
        danger: "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25",
      },
      size: {
        sm: "text-xs px-3 py-1.5",
        md: "text-sm px-4 py-2",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {
  loading?: boolean;
}

export function Button({
  className,
  variant,
  size,
  loading,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(button({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
