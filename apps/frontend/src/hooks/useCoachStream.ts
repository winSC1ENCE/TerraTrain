"use client";

import { useCallback, useRef, useState } from "react";
import type { CoachingRequest, CoachingSSEEvent } from "@/lib/types";

interface CoachStreamState {
  thinking: string[];
  toolCalls: string[];
  plan: Record<string, unknown> | null;
  error: string | null;
  isStreaming: boolean;
}

export function useCoachStream() {
  const [state, setState] = useState<CoachStreamState>({
    thinking: [],
    toolCalls: [],
    plan: null,
    error: null,
    isStreaming: false,
  });
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (request: CoachingRequest) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setState({ thinking: [], toolCalls: [], plan: null, error: null, isStreaming: true });

    const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    try {
      const res = await fetch(`${BASE}/api/v1/coaching/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: abortRef.current.signal,
      });

      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({ detail: "Stream failed" }));
        setState((s) => ({ ...s, error: err.detail, isStreaming: false }));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            // handled below
          } else if (line.startsWith("data:")) {
            // SSE data line — parse previous event + data pair
            // Simple approach: emit the raw line
          }
        }

        // Proper SSE parsing
        const events = buffer
          .split("\n\n")
          .filter((b) => b.includes("event:") && b.includes("data:"));
        for (const block of events) {
          const eventLine = block.split("\n").find((l) => l.startsWith("event:"));
          const dataLine = block.split("\n").find((l) => l.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const eventType = eventLine.replace("event:", "").trim();
          const data = dataLine.replace("data:", "").trim();

          try {
            const parsed = JSON.parse(data);
            handleEvent(eventType, parsed);
          } catch {
            handleEvent(eventType, data);
          }
        }
        buffer = "";
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setState((s) => ({ ...s, error: (err as Error).message, isStreaming: false }));
      }
    } finally {
      setState((s) => ({ ...s, isStreaming: false }));
    }

    function handleEvent(event: string, data: unknown) {
      setState((s) => {
        switch (event) {
          case "thinking":
            return { ...s, thinking: [...s.thinking, String(data)] };
          case "tool_call":
          case "tool_result":
            return { ...s, toolCalls: [...s.toolCalls, String(data)] };
          case "workout_plan":
            return { ...s, plan: data as Record<string, unknown>, isStreaming: false };
          case "error":
            return { ...s, error: String(data), isStreaming: false };
          default:
            return s;
        }
      });
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, start, stop };
}
