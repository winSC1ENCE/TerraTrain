"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Workout } from "@/lib/types";
import { formatDuration } from "@/lib/utils";

export default function WorkoutsPage() {
  const [athleteId, setAthleteId] = useState("");
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [pushing, setPushing] = useState<string | null>(null);

  async function loadWorkouts() {
    if (!athleteId) return;
    const data = await api.workouts.list(athleteId);
    setWorkouts(data);
  }

  async function handlePush(id: string) {
    setPushing(id);
    try {
      const updated = await api.workouts.push(id);
      setWorkouts((ws) => ws.map((w) => (w.id === id ? updated : w)));
    } finally {
      setPushing(null);
    }
  }

  const statusColors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    approved: "bg-blue-100 text-blue-700",
    pushed: "bg-green-100 text-green-700",
    completed: "bg-purple-100 text-purple-700",
    archived: "bg-gray-200 text-gray-400",
  };

  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Workouts</h1>

      <div className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="Athlete ID"
          value={athleteId}
          onChange={(e) => setAthleteId(e.target.value)}
          className="flex-1 rounded border px-3 py-2 text-sm"
        />
        <button onClick={loadWorkouts} className="px-4 py-2 border rounded text-sm">
          Load
        </button>
      </div>

      <div className="space-y-4">
        {workouts.map((w) => (
          <div key={w.id} className="rounded border p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="font-medium">{w.name}</p>
                <p className="text-sm text-gray-500">
                  {w.workout_type} &middot;{" "}
                  {w.duration_seconds ? formatDuration(w.duration_seconds) : "—"} &middot; TSS{" "}
                  {w.target_tss?.toFixed(0) ?? "—"}
                  {w.scheduled_date ? ` · ${w.scheduled_date}` : ""}
                </p>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded ${statusColors[w.status] ?? "bg-gray-100"}`}
              >
                {w.status}
              </span>
            </div>

            {w.structured_text && (
              <pre className="text-xs bg-gray-50 dark:bg-gray-900 rounded p-3 mb-3 overflow-x-auto whitespace-pre-wrap">
                {w.structured_text}
              </pre>
            )}

            {w.status === "draft" && (
              <button
                onClick={() => handlePush(w.id)}
                disabled={pushing === w.id}
                className="text-sm px-3 py-1 border rounded disabled:opacity-50"
              >
                {pushing === w.id ? "Pushing..." : "Push to Intervals.icu"}
              </button>
            )}
            {w.intervals_workout_id && (
              <p className="text-xs text-gray-400 mt-1">
                Intervals ID: {w.intervals_workout_id}
              </p>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
