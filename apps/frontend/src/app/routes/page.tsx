"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Route } from "@/lib/types";
import { formatDistance } from "@/lib/utils";

export default function RoutesPage() {
  const [athleteId, setAthleteId] = useState("");
  const [routes, setRoutes] = useState<Route[]>([]);
  const [uploading, setUploading] = useState(false);
  const [routeName, setRouteName] = useState("");
  const [file, setFile] = useState<File | null>(null);

  async function loadRoutes() {
    if (!athleteId) return;
    const data = await api.routes.list(athleteId);
    setRoutes(data);
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !athleteId || !routeName) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("athlete_id", athleteId);
      form.append("name", routeName);
      form.append("gpx_file", file);
      await api.routes.upload(form);
      await loadRoutes();
      setFile(null);
      setRouteName("");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Routes</h1>

      <div className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="Athlete ID"
          value={athleteId}
          onChange={(e) => setAthleteId(e.target.value)}
          className="flex-1 rounded border px-3 py-2 text-sm"
        />
        <button
          onClick={loadRoutes}
          className="px-4 py-2 border rounded text-sm"
        >
          Load Routes
        </button>
      </div>

      <form onSubmit={handleUpload} className="mb-8 space-y-3">
        <h2 className="font-medium">Upload GPX</h2>
        <input
          type="text"
          placeholder="Route name"
          value={routeName}
          onChange={(e) => setRouteName(e.target.value)}
          className="w-full rounded border px-3 py-2 text-sm"
        />
        <input
          type="file"
          accept=".gpx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <button
          type="submit"
          disabled={uploading || !file || !athleteId || !routeName}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload & Analyze"}
        </button>
      </form>

      {routes.length > 0 && (
        <div className="space-y-3">
          {routes.map((r) => (
            <div key={r.id} className="rounded border p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{r.name}</p>
                  <p className="text-sm text-gray-500">
                    {formatDistance(r.distance_m)} &middot;{" "}
                    {Math.round(r.elevation_gain_m)} m gain &middot;{" "}
                    {r.climb_profile.length} climb(s)
                  </p>
                </div>
                {r.terrain_score !== null && (
                  <span className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                    terrain {(r.terrain_score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {r.climb_profile.length > 0 && (
                <div className="mt-2 space-y-1">
                  {r.climb_profile.slice(0, 3).map((c, i) => (
                    <p key={i} className="text-xs text-gray-500">
                      Climb {i + 1}: km {c.start_km}–{c.end_km}, {c.avg_grade_pct}% avg
                      {c.category ? ` (${c.category})` : ""}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
