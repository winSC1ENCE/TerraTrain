"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Map, Mountain, Ruler } from "lucide-react";
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

  const { data: routes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(athlete!.id),
    enabled: !!athlete,
  });

  if (!athlete) return null;

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
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h2 className="text-sm font-semibold text-text">{r.name}</h2>
                  {r.terrain_score != null && (
                    <Badge variant="accent">
                      {t.routes.terrainScore} {(r.terrain_score * 100).toFixed(0)}%
                    </Badge>
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
