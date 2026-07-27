"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Eye, Map, Mountain, Pencil, Ruler, Trash, X, ArrowUpRight, ArrowDownRight, Layers, Flame } from "lucide-react";
import { api, Route } from "@/lib/api";
import type { ClimbSegment } from "@/lib/types";
import { useAthlete } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { UploadZone } from "@/components/knowledge/UploadZone";
import { formatDistance } from "@/lib/utils";

import type { TrackPoint } from "@/components/routes/RouteMap";

const RouteMap = dynamic(() => import("@/components/routes/RouteMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[340px] bg-surface rounded-xl border border-border flex items-center justify-center text-text-muted text-xs animate-pulse">
      Karte wird geladen...
    </div>
  ),
});

const ElevationProfile = dynamic(() => import("@/components/routes/ElevationProfile"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[180px] bg-surface rounded-xl border border-border flex items-center justify-center text-text-muted text-xs animate-pulse">
      Höhenprofil wird geladen...
    </div>
  ),
});

function getCategoryBadge(cat?: string | null) {
  const c = (cat || "").toLowerCase();
  if (c.includes("hc") || c.includes("cat1")) {
    return <Badge className="bg-red-500/15 text-red-500 border-red-500/30 text-[10px] px-1.5 py-0">{cat?.toUpperCase()}</Badge>;
  }
  if (c.includes("cat2") || c.includes("cat3")) {
    return <Badge className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-[10px] px-1.5 py-0">{cat?.toUpperCase()}</Badge>;
  }
  if (c.includes("cat4")) {
    return <Badge className="bg-emerald-500/15 text-emerald-500 border-emerald-500/30 text-[10px] px-1.5 py-0">{cat?.toUpperCase()}</Badge>;
  }
  return <Badge variant="accent" className="text-[10px] px-1.5 py-0">{cat ? cat.toUpperCase() : "ANSTIEG"}</Badge>;
}

export default function RoutesPage() {
  const athlete = useAthlete();
  const t = useT();
  const queryClient = useQueryClient();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [activeClimbIndex, setActiveClimbIndex] = useState<number | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<TrackPoint | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedRoute(null);
        setHoveredPoint(null);
      }
    };

    if (selectedRoute) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedRoute]);

  const { data: routes } = useQuery({
    queryKey: ["routes"],
    queryFn: () => api.routes.list(),
  });

  if (!athlete) return null;

  const startEdit = (id: string, currentName: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEditingId(id);
    setEditName(currentName);
  };

  const cancelEdit = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEditingId(null);
    setEditName("");
  };

  const handleSaveRename = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!editName.trim()) return;
    setIsSaving(true);
    try {
      await api.routes.update(id, { name: editName.trim() });
      void queryClient.invalidateQueries({ queryKey: ["routes"] });
      if (selectedRoute?.id === id) {
        setSelectedRoute((prev) => (prev ? { ...prev, name: editName.trim() } : null));
      }
      setEditingId(null);
    } catch (err) {
      console.error("Failed to rename route", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!window.confirm("Möchtest du diese Route wirklich löschen?")) return;
    try {
      await api.routes.delete(id);
      void queryClient.invalidateQueries({ queryKey: ["routes"] });
      if (selectedRoute?.id === id) {
        setSelectedRoute(null);
      }
    } catch (err) {
      console.error("Failed to delete route", err);
    }
  };

  async function handleUpload(file: File): Promise<string> {
    const form = new FormData();
    form.append("name", file.name.replace(/\.gpx$/i, "").replace(/[_-]/g, " "));
    form.append("sport", athlete!.sport);
    form.append("gpx_file", file);
    const route = await api.routes.upload(form);
    void queryClient.invalidateQueries({ queryKey: ["routes"] });
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
            <Card
              key={r.id}
              className="cursor-pointer hover:border-accent/60 transition-all group"
              onClick={() => {
                setSelectedRoute(r);
                setActiveClimbIndex(null);
                setHoveredPoint(null);
              }}
            >
              <CardBody className="pt-4">
                <div className="mb-2 flex items-center justify-between gap-2 min-h-8">
                  {editingId === r.id ? (
                    <div className="flex items-center gap-1.5 flex-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="px-2 py-1 text-xs bg-bg border border-border rounded flex-1 focus:outline-none focus:ring-1 focus:ring-accent text-text"
                        disabled={isSaving}
                      />
                      <button
                        type="button"
                        onClick={(e) => handleSaveRename(r.id, e)}
                        disabled={isSaving}
                        className="p-1 hover:text-success text-text-muted transition-colors"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={(e) => cancelEdit(e)}
                        disabled={isSaving}
                        className="p-1 hover:text-danger text-text-muted transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between w-full gap-2">
                      <div className="flex items-center gap-1.5">
                        <h2 className="text-sm font-semibold text-text group-hover:text-accent transition-colors">{r.name}</h2>
                        <button
                          type="button"
                          onClick={(e) => startEdit(r.id, r.name, e)}
                          className="p-0.5 opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-accent text-text-muted transition-opacity transition-colors"
                          title="Umbenennen"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={(e) => handleDelete(r.id, e)}
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
                  <ul className="mt-3 space-y-1 border-t border-border/40 pt-2">
                    {r.climb_profile.slice(0, 3).map((c: ClimbSegment, i: number) => (
                      <li key={i} className="flex items-center justify-between text-xs text-text-muted">
                        <span className="tabular-nums">
                          km {c.start_km}–{c.end_km} ({(c.length_m / 1000).toFixed(1)} km)
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="tabular-nums font-medium text-text">{c.avg_grade_pct}%</span>
                          {getCategoryBadge(c.category)}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="mt-3 flex items-center justify-end text-xs font-semibold text-accent gap-1 group-hover:underline">
                  <Eye className="h-3.5 w-3.5" />
                  <span>Karte & Details anzeigen</span>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* ROUTE DETAIL MODAL */}
      {selectedRoute && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setSelectedRoute(null)}
        >
          <div
            className="bg-bg border border-border rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface/80">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-accent/10 text-accent">
                  <Map className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-text flex items-center gap-2">
                    {selectedRoute.name}
                    <button
                      type="button"
                      onClick={(e) => startEdit(selectedRoute.id, selectedRoute.name, e)}
                      className="text-text-muted hover:text-accent transition-colors"
                      title="Umbenennen"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                  </h2>
                  <p className="text-xs text-text-muted uppercase tracking-wider font-semibold">
                    {selectedRoute.sport} · {formatDistance(selectedRoute.distance_m)} · {Math.round(selectedRoute.elevation_gain_m)} hm
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {selectedRoute.terrain_score != null && (
                  <Badge variant="accent" className="text-xs">
                    Terrain Score {(selectedRoute.terrain_score * 100).toFixed(0)}%
                  </Badge>
                )}
                <button
                  type="button"
                  onClick={() => setSelectedRoute(null)}
                  className="p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {/* Interactive Open-Source Leaflet Map */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted mb-2 flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-accent" />
                  Interaktive Topografische Karte & Anstiege
                </h3>
                <RouteMap
                  trackPoints={selectedRoute.analysis?.track_points || []}
                  climbs={selectedRoute.climb_profile}
                  activeClimbIndex={activeClimbIndex}
                  hoveredPoint={hoveredPoint}
                  onClimbClick={(idx) => setActiveClimbIndex(idx)}
                />
              </div>

              {/* Elevation Profile Chart with Marked Climb Segments */}
              {selectedRoute.analysis?.track_points && selectedRoute.analysis.track_points.length > 0 && (
                <ElevationProfile
                  trackPoints={selectedRoute.analysis.track_points}
                  climbs={selectedRoute.climb_profile}
                  activeClimbIndex={activeClimbIndex}
                  onClimbClick={(idx) => setActiveClimbIndex(idx)}
                  onHoverPoint={(pt) => setHoveredPoint(pt)}
                />
              )}

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-surface p-3 rounded-xl border border-border/60">
                  <span className="text-[10px] uppercase font-bold text-text-muted flex items-center gap-1">
                    <Ruler className="h-3 w-3 text-accent" /> Distanz
                  </span>
                  <p className="text-base font-bold text-text mt-0.5">{formatDistance(selectedRoute.distance_m)}</p>
                </div>
                <div className="bg-surface p-3 rounded-xl border border-border/60">
                  <span className="text-[10px] uppercase font-bold text-text-muted flex items-center gap-1">
                    <ArrowUpRight className="h-3 w-3 text-emerald-500" /> Höhenmeter
                  </span>
                  <p className="text-base font-bold text-text mt-0.5">+{Math.round(selectedRoute.elevation_gain_m)} hm</p>
                  <p className="text-[10px] text-text-muted">-{Math.round(selectedRoute.elevation_loss_m || 0)} hm Abfahrt</p>
                </div>
                <div className="bg-surface p-3 rounded-xl border border-border/60">
                  <span className="text-[10px] uppercase font-bold text-text-muted flex items-center gap-1">
                    <Mountain className="h-3 w-3 text-purple-500" /> Höchster Punkt
                  </span>
                  <p className="text-base font-bold text-text mt-0.5">
                    {selectedRoute.max_elevation_m ? `${Math.round(selectedRoute.max_elevation_m)} m` : "-"}
                  </p>
                  <p className="text-[10px] text-text-muted">
                    Min: {selectedRoute.min_elevation_m ? `${Math.round(selectedRoute.min_elevation_m)} m` : "-"}
                  </p>
                </div>
                <div className="bg-surface p-3 rounded-xl border border-border/60">
                  <span className="text-[10px] uppercase font-bold text-text-muted flex items-center gap-1">
                    <Flame className="h-3 w-3 text-amber-500" /> Anstiege Gesamt
                  </span>
                  <p className="text-base font-bold text-text mt-0.5">{selectedRoute.climb_profile.length}</p>
                  <p className="text-[10px] text-text-muted">Surface: {selectedRoute.surface_type || "Strasse"}</p>
                </div>
              </div>

              {/* All Climbs Table */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                    <Flame className="h-3.5 w-3.5 text-amber-500" />
                    Alle Anstiege ({selectedRoute.climb_profile.length})
                  </h3>
                  {activeClimbIndex != null && (
                    <button
                      type="button"
                      onClick={() => setActiveClimbIndex(null)}
                      className="text-[10px] text-accent hover:underline"
                    >
                      Karten-Fokus zurücksetzen
                    </button>
                  )}
                </div>

                {!selectedRoute.climb_profile.length ? (
                  <p className="text-xs text-text-muted italic bg-surface p-4 rounded-xl text-center">
                    Keine signifikanten Anstiege auf dieser Route erkannt.
                  </p>
                ) : (
                  <div className="overflow-x-auto border border-border rounded-xl bg-surface">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-surface-2 border-b border-border text-[10px] uppercase text-text-muted">
                        <tr>
                          <th className="py-2.5 px-3">#</th>
                          <th className="py-2.5 px-3">Distanz (km)</th>
                          <th className="py-2.5 px-3">Länge</th>
                          <th className="py-2.5 px-3">Höhengewinn</th>
                          <th className="py-2.5 px-3">Ø Steigung</th>
                          <th className="py-2.5 px-3">Max Steigung</th>
                          <th className="py-2.5 px-3">VAM</th>
                          <th className="py-2.5 px-3">Kategorie</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {selectedRoute.climb_profile.map((c: ClimbSegment, i: number) => {
                          const isActive = activeClimbIndex === i;
                          return (
                            <tr
                              key={i}
                              onMouseEnter={() => setActiveClimbIndex(i)}
                              onClick={() => setActiveClimbIndex(i)}
                              className={`transition-colors cursor-pointer ${
                                isActive ? "bg-accent/15 font-semibold text-text" : "hover:bg-surface-2/70 text-text-muted"
                              }`}
                            >
                              <td className="py-2.5 px-3 text-text font-bold">{i + 1}</td>
                              <td className="py-2.5 px-3 tabular-nums">km {c.start_km} – {c.end_km}</td>
                              <td className="py-2.5 px-3 tabular-nums">{(c.length_m / 1000).toFixed(1)} km</td>
                              <td className="py-2.5 px-3 tabular-nums text-emerald-500 font-medium">+{Math.round(c.elevation_gain_m)} hm</td>
                              <td className="py-2.5 px-3 tabular-nums font-bold text-text">{c.avg_grade_pct}%</td>
                              <td className="py-2.5 px-3 tabular-nums">{c.max_grade_pct}%</td>
                              <td className="py-2.5 px-3 tabular-nums">{c.vam ? `${Math.round(c.vam)} m/h` : "-"}</td>
                              <td className="py-2.5 px-3">{getCategoryBadge(c.category)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
