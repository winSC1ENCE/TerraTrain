"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Dumbbell, Send } from "lucide-react";
import { api } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn, formatDate, formatDuration } from "@/lib/utils";

const statusVariant: Record<string, "default" | "info" | "success" | "accent"> = {
  draft: "default",
  approved: "info",
  pushed: "success",
  completed: "accent",
};

export default function WorkoutsPage() {
  const athlete = useAthlete();
  const t = useT();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: workouts } = useQuery({
    queryKey: ["workouts", athlete?.id],
    queryFn: () => api.workouts.list(athlete!.id),
    enabled: !!athlete,
  });

  const pushMutation = useMutation({
    mutationFn: api.workouts.push,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["workouts", athlete?.id] }),
  });

  if (!athlete) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold tracking-tight">{t.workouts.title}</h1>

      {!workouts?.length ? (
        <EmptyState
          icon={Dumbbell}
          title={t.workouts.empty}
          description={t.workouts.emptyHint}
          action={
            <Link href="/coach">
              <Button size="sm">{t.workouts.goToCoach}</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {workouts.map((w) => {
            const isOpen = expanded === w.id;
            return (
              <Card key={w.id}>
                <CardBody className="pt-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="truncate text-sm font-semibold text-text">{w.name}</h2>
                      <p className="mt-0.5 text-xs text-text-muted">
                        {t.coach.types[w.workout_type] ?? w.workout_type}
                        {w.duration_seconds ? ` · ${formatDuration(w.duration_seconds)}` : ""}
                        {w.target_tss ? ` · TSS ${Math.round(w.target_tss)}` : ""}
                        {w.scheduled_date ? ` · ${formatDate(w.scheduled_date)}` : ""}
                      </p>
                    </div>
                    <Badge variant={statusVariant[w.status] ?? "default"}>
                      {t.workouts.status[w.status] ?? w.status}
                    </Badge>
                  </div>

                  {w.structured_text && (
                    <button
                      type="button"
                      onClick={() => setExpanded(isOpen ? null : w.id)}
                      className="mt-2 flex items-center gap-1 text-xs text-text-muted transition-colors hover:text-text-secondary"
                    >
                      <ChevronDown
                        className={cn("h-3.5 w-3.5 transition-transform", isOpen && "rotate-180")}
                      />
                      Intervals.icu
                    </button>
                  )}
                  {isOpen && w.structured_text && (
                    <div className="mt-2">
                      <CodeBlock code={w.structured_text} />
                    </div>
                  )}

                  {w.status === "draft" && w.structured_text && (
                    <div className="mt-3">
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={pushMutation.isPending && pushMutation.variables === w.id}
                        onClick={() => pushMutation.mutate(w.id)}
                      >
                        <Send className="h-3.5 w-3.5" />
                        {t.workouts.push}
                      </Button>
                    </div>
                  )}
                </CardBody>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
