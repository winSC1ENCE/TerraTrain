"use client";

import { useState } from "react";
import { useCoachStream } from "@/hooks/useCoachStream";

const WORKOUT_TYPES = [
  "endurance",
  "tempo",
  "threshold",
  "vo2max",
  "recovery",
  "race_simulation",
];

export default function CoachPage() {
  const [athleteId, setAthleteId] = useState("");
  const [workoutType, setWorkoutType] = useState("threshold");
  const [notes, setNotes] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");

  const { thinking, toolCalls, plan, error, isStreaming, start, stop } = useCoachStream();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!athleteId) return;
    start({
      athlete_id: athleteId,
      workout_type: workoutType,
      scheduled_date: scheduledDate || undefined,
      notes: notes || undefined,
    });
  }

  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">AI Coach</h1>

      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        <div>
          <label className="block text-sm font-medium mb-1">Athlete ID</label>
          <input
            type="text"
            value={athleteId}
            onChange={(e) => setAthleteId(e.target.value)}
            placeholder="UUID from /api/v1/athletes"
            className="w-full rounded border px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Workout Type</label>
          <select
            value={workoutType}
            onChange={(e) => setWorkoutType(e.target.value)}
            className="w-full rounded border px-3 py-2 text-sm"
          >
            {WORKOUT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Scheduled Date</label>
          <input
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
            className="w-full rounded border px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Notes (optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full rounded border px-3 py-2 text-sm"
            placeholder="Any special requests or constraints..."
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isStreaming || !athleteId}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
          >
            {isStreaming ? "Generating..." : "Generate Workout"}
          </button>
          {isStreaming && (
            <button
              type="button"
              onClick={stop}
              className="px-4 py-2 border rounded text-sm"
            >
              Stop
            </button>
          )}
        </div>
      </form>

      {(thinking.length > 0 || toolCalls.length > 0 || plan || error) && (
        <div className="space-y-4">
          {thinking.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Agent Reasoning
              </h2>
              <div className="rounded bg-gray-50 dark:bg-gray-900 p-4 text-sm space-y-1 max-h-48 overflow-y-auto">
                {thinking.map((t, i) => (
                  <p key={i} className="text-gray-600 dark:text-gray-400">
                    {t}
                  </p>
                ))}
              </div>
            </section>
          )}

          {toolCalls.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Tool Calls
              </h2>
              <div className="rounded bg-gray-50 dark:bg-gray-900 p-4 text-xs font-mono space-y-1 max-h-32 overflow-y-auto">
                {toolCalls.map((t, i) => (
                  <p key={i}>{t}</p>
                ))}
              </div>
            </section>
          )}

          {error && (
            <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {plan && (
            <section>
              <h2 className="text-lg font-semibold mb-2">
                {(plan as { name?: string }).name ?? "Workout Plan"}
              </h2>
              <div className="rounded bg-green-50 dark:bg-green-950 p-4 mb-4">
                <p className="text-sm text-green-700 dark:text-green-300">
                  TSS target:{" "}
                  <strong>{(plan as { target_tss?: number }).target_tss ?? "?"}</strong>
                </p>
              </div>
              {(plan as { structured_text?: string }).structured_text && (
                <pre className="rounded bg-gray-900 text-green-400 p-4 text-sm overflow-x-auto whitespace-pre-wrap">
                  {(plan as { structured_text: string }).structured_text}
                </pre>
              )}
              {(plan as { rationale?: string }).rationale && (
                <div className="mt-4">
                  <h3 className="font-medium text-sm mb-1">Coach Rationale</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {(plan as { rationale: string }).rationale}
                  </p>
                </div>
              )}
              {(plan as { workout_id?: string }).workout_id && (
                <div className="mt-4 flex gap-2">
                  <a
                    href={`/workouts/${(plan as { workout_id: string }).workout_id}`}
                    className="px-4 py-2 border rounded text-sm"
                  >
                    View Workout
                  </a>
                </div>
              )}
            </section>
          )}
        </div>
      )}
    </main>
  );
}
