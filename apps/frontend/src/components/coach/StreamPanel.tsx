"use client";

import { useEffect, useRef } from "react";
import { Brain, Wrench } from "lucide-react";
import type { CoachEvent } from "@/hooks/useCoachStream";
import { useT } from "@/lib/i18n";

export function StreamPanel({
  events,
  isStreaming,
}: {
  events: CoachEvent[];
  isStreaming: boolean;
}) {
  const t = useT();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [events.length]);

  return (
    <div className="max-h-72 space-y-1.5 overflow-y-auto rounded-lg bg-bg border border-border p-3">
      {events.map((e, i) =>
        e.kind === "thinking" ? (
          <div key={i} className="flex items-start gap-2 text-xs italic text-text-muted">
            <Brain className="mt-0.5 shrink-0" style={{ width: 13, height: 13 }} />
            <span>{e.text}</span>
          </div>
        ) : (
          <div
            key={i}
            className="flex items-start gap-2 rounded-md bg-surface-2 px-2 py-1 font-mono text-[11px] text-text-secondary"
          >
            <Wrench className="mt-0.5 shrink-0" style={{ width: 12, height: 12 }} />
            <span className="break-all">{e.text}</span>
          </div>
        )
      )}
      {isStreaming && (
        <div className="flex items-center gap-1.5 pt-1 text-xs text-text-muted">
          <span className="flex gap-1">
            <Dot delay="0ms" />
            <Dot delay="150ms" />
            <Dot delay="300ms" />
          </span>
          {t.coach.thinking}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent"
      style={{ animationDelay: delay }}
    />
  );
}
