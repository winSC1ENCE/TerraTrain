"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Dumbbell, Send, Pencil } from "lucide-react";
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

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editStructuredText, setEditStructuredText] = useState("");

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

  const updateMutation = useMutation({
    mutationFn: ({ id, name, structured_text }: { id: string; name: string; structured_text: string }) =>
      api.workouts.update(id, { name, structured_text }),
    onSuccess: () => {
      setEditingId(null);
      void queryClient.invalidateQueries({ queryKey: ["workouts", athlete?.id] });
    },
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
            const isEditing = editingId === w.id;

            if (isEditing) {
              return (
                <Card key={w.id}>
                  <CardBody className="pt-4 space-y-4">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-text-muted">Workout-Name</label>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-text-muted">Intervals.icu Schritte</label>
                      <textarea
                        value={editStructuredText}
                        onChange={(e) => setEditStructuredText(e.target.value)}
                        rows={6}
                        className="w-full px-3 py-2 text-sm font-mono bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
                      />
                    </div>

                    <div className="flex gap-2 justify-end pt-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setEditingId(null)}
                      >
                        Abbrechen
                      </Button>
                      <Button
                        size="sm"
                        loading={updateMutation.isPending}
                        onClick={() =>
                          updateMutation.mutate({
                            id: w.id,
                            name: editName,
                            structured_text: editStructuredText,
                          })
                        }
                      >
                        Speichern
                      </Button>
                    </div>
                  </CardBody>
                </Card>
              );
            }

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

                  <div className="mt-3 flex gap-2">
                    {w.status === "draft" && w.structured_text && (
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={pushMutation.isPending && pushMutation.variables === w.id}
                        onClick={() => pushMutation.mutate(w.id)}
                      >
                        <Send className="h-3.5 w-3.5" />
                        {t.workouts.push}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setEditingId(w.id);
                        setEditName(w.name);
                        setEditStructuredText(w.structured_text ?? "");
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Bearbeiten
                    </Button>
                  </div>
                </CardBody>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
