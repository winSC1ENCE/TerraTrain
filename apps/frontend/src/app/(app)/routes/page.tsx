"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Map, Mountain, Pencil, Ruler, Trash, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { UploadZone } from "@/components/knowledge/UploadZone";
import { formatDistance } from "@/lib/utils";

export default function RoutesPage() {
  const athlete = useAthlete();
  const t = useT();
  const queryClient = useQueryClient();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const { data: routes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(athlete!.id),
    enabled: !!athlete,
  });

  if (!athlete) return null;

  const startEdit = (id: string, currentName: string) => {
    setEditingId(id);
    setEditName(currentName);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
  };

  const handleSaveRename = async (id: string) => {
    if (!editName.trim()) return;
    setIsSaving(true);
    try {
      await api.routes.update(id, { name: editName.trim() });
      void queryClient.invalidateQueries({ queryKey: ["routes", athlete.id] });
      setEditingId(null);
    } catch (err) {
      console.error("Failed to rename route", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Möchtest du diese Route wirklich löschen?")) return;
    try {
      await api.routes.delete(id);
      void queryClient.invalidateQueries({ queryKey: ["routes", athlete.id] });
    } catch (err) {
      console.error("Failed to delete route", err);
    }
  };

  async function handleUpload(file: File): Promise<string> {
    const form = new FormData();
    form.append("athlete_id", athlete!.id);
    form.append("name", file.name.replace(/\.gpx$/i, "").replace(/[_-]/g, " "));
    form.append("sport", athlete!.sport);
    form.append("gpx_file", file);
    const route = await api.routes.upload(form);
    void queryClient.invalidateQueries({ queryKey: ["routes", athlete!.id] });
    return `${(route.distance_m / 1000).toFixed(1)} km · ${Math.round(route.elevation_gain_m)} hm`;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold tracking-tight">{t.routes.title}</h1>

      <UploadZone
        accept=".gpx,application/gpx+xml"
        hint={t.routes.dropHint}
        onUpload={handleUpload}
      />

      {!routes?.length ? (
        <EmptyState icon={Map} title={t.routes.empty} description={t.routes.emptyHint} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {routes.map((r) => (
            <Card key={r.id}>
              <CardBody className="pt-4">
                <div className="mb-2 flex items-center justify-between gap-2 min-h-8">
                  {editingId === r.id ? (
                    <div className="flex items-center gap-1.5 flex-1">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="px-2 py-1 text-xs bg-bg border border-border rounded flex-1 focus:outline-none focus:ring-1 focus:ring-accent text-text"
                        disabled={isSaving}
                      />
                      <button
                        type="button"
                        onClick={() => handleSaveRename(r.id)}
                        disabled={isSaving}
                        className="p-1 hover:text-success text-text-muted transition-colors"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        disabled={isSaving}
                        className="p-1 hover:text-danger text-text-muted transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between w-full gap-2">
                      <div className="flex items-center gap-1.5 group">
                        <h2 className="text-sm font-semibold text-text">{r.name}</h2>
                        <button
                          type="button"
                          onClick={() => startEdit(r.id, r.name)}
                          className="p-0.5 opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-accent text-text-muted transition-opacity transition-colors"
                          title="Umbenennen"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleDelete(r.id)}
                          className="p-1 text-text-muted hover:text-danger hover:bg-danger/10 rounded transition-colors"
                          title="Löschen"
                        >
                          <Trash className="h-3.5 w-3.5" />
                        </button>
                        {r.terrain_score != null && (
                          <Badge variant="accent">
                            {t.routes.terrainScore} {(r.terrain_score * 100).toFixed(0)}%
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                <div className="flex gap-4 text-xs text-text-muted">
                  <span className="flex items-center gap-1">
                    <Ruler className="h-3.5 w-3.5" />
                    {formatDistance(r.distance_m)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Mountain className="h-3.5 w-3.5" />
                    {Math.round(r.elevation_gain_m)} hm
                  </span>
                  <span>
                    {r.climb_profile.length} {t.routes.climbs}
                  </span>
                </div>
                {r.climb_profile.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {r.climb_profile.slice(0, 3).map((c, i) => (
                      <li key={i} className="flex items-center gap-2 text-xs text-text-muted">
                        <span className="tabular-nums">
                          km {c.start_km}–{c.end_km}
                        </span>
                        <span className="tabular-nums">{c.avg_grade_pct}%</span>
                        {c.category && (
                          <Badge variant="warning" className="text-[10px] px-1.5 py-0">
                            {c.category.toUpperCase()}
                          </Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
