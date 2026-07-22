"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

export function CodeBlock({ code, className }: { code: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className={cn("relative rounded-lg bg-bg border border-border", className)}>
      <button
        type="button"
        onClick={copy}
        className="absolute right-2 top-2 rounded-md p-1.5 text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
        aria-label="Copy"
      >
        {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
      </button>
      <pre className="overflow-x-auto p-4 pr-12 text-xs font-mono text-text-secondary whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  );
}
