"use client";

import { useCallback, useRef, useState } from "react";
import { API_BASE, csrfHeaders } from "@/lib/api";
import type { CoachPlan, CoachingRequest } from "@/lib/types";

export interface CoachEvent {
  kind: "thinking" | "tool_call" | "tool_result";
  text: string;
}

interface CoachStreamState {
  events: CoachEvent[];
  plan: CoachPlan | null;
  error: string | null;
  isStreaming: boolean;
}

const INITIAL: CoachStreamState = {
  events: [],
  plan: null,
  error: null,
  isStreaming: false,
};

export function useCoachStream() {
  const [state, setState] = useState<CoachStreamState>(INITIAL);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (request: CoachingRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ ...INITIAL, isStreaming: true });

    function handleEvent(event: string, data: unknown) {
      setState((s) => {
        switch (event) {
          case "thinking":
            return { ...s, events: [...s.events, { kind: "thinking", text: String(data) }] };
          case "tool_call":
            return { ...s, events: [...s.events, { kind: "tool_call", text: String(data) }] };
          case "tool_result":
            return {
              ...s,
              events: [...s.events, { kind: "tool_result", text: String(data) }],
            };
          case "workout_plan":
            return { ...s, plan: data as CoachPlan, isStreaming: false };
          case "error":
            return { ...s, error: String(data), isStreaming: false };
          default:
            return s;
        }
      });
    }

    function processBlock(block: string) {
      let eventType = "";
      let dataRaw = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        else if (line.startsWith("data:")) dataRaw += line.slice(5).trim();
      }
      if (!eventType) return;
      try {
        handleEvent(eventType, JSON.parse(dataRaw));
      } catch {
        handleEvent(eventType, dataRaw);
      }
    }

    try {
      const res = await fetch(`${API_BASE}/coaching/generate`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({ detail: "Stream failed" }));
        setState((s) => ({ ...s, error: err.detail, isStreaming: false }));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      // SSE parsing: append to buffer, split on the event delimiter "\n\n",
      // process every COMPLETE block, keep the trailing partial block as the
      // new buffer. (Events split across network chunks are preserved.)
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          if (block.trim()) processBlock(block);
        }
      }
      // Flush any final complete block left in the buffer
      if (buffer.trim()) processBlock(buffer);
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setState((s) => ({ ...s, error: (err as Error).message, isStreaming: false }));
      }
    } finally {
      setState((s) => ({ ...s, isStreaming: false }));
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  const reset = useCallback(() => setState(INITIAL), []);

  return { ...state, start, stop, reset };
}
