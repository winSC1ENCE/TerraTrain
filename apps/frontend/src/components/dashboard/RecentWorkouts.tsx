"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Dumbbell } from "lucide-react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

const statusVariant: Record<string, "default" | "info" | "success" | "accent"> = {
  draft: "default",
  approved: "info",
  pushed: "success",
  completed: "accent",
};

export function RecentWorkouts({ athleteId }: { athleteId: string }) {
  const t = useT();
  const { data: workouts } = useQuery({
    queryKey: ["workouts", athleteId],
    queryFn: () => api.workouts.list(athleteId),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.dashboard.recentWorkouts}</CardTitle>
      </CardHeader>
      <CardBody>
        {!workouts?.length ? (
          <EmptyState icon={Dumbbell} title={t.dashboard.noWorkouts} />
        ) : (
          <ul className="divide-y divide-border">
            {workouts.slice(0, 5).map((w) => (
              <li key={w.id}>
                <Link
                  href="/workouts"
                  className="flex items-center justify-between gap-3 py-2.5 hover:bg-surface-2/50 -mx-2 px-2 rounded-lg transition-colors"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm text-text">{w.name}</p>
                    <p className="text-xs text-text-muted">
                      {t.coach.types[w.workout_type] ?? w.workout_type}
                      {w.scheduled_date ? ` · ${formatDate(w.scheduled_date)}` : ""}
                      {w.target_tss ? ` · TSS ${Math.round(w.target_tss)}` : ""}
                    </p>
                  </div>
                  <Badge variant={statusVariant[w.status] ?? "default"}>
                    {t.workouts.status[w.status] ?? w.status}
                  </Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
