"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Dumbbell, Send, Pencil, Trash } from "lucide-react";
import { api } from "@/lib/api";
import { useAthlete, useAthleteStore } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn, formatDate, formatDuration } from "@/lib/utils";
import { PhaseBar } from "@/components/coach/PhaseBar";
import type { Sport, WorkoutPhase } from "@/lib/types";

const statusVariant: Record<string, "default" | "info" | "success" | "accent"> = {
  draft: "default",
  approved: "info",
  pushed: "success",
  completed: "accent",
};

export default function WorkoutsPage() {
  const athlete = useAthlete();
  const language = useAthleteStore((s) => s.language);
  const t = useT();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editStructuredText, setEditStructuredText] = useState("");
  const [editSport, setEditSport] = useState<Sport>("cycling");
  const [editPressLap, setEditPressLap] = useState(false);

  const { data: workouts } = useQuery({
    queryKey: ["workouts", athlete?.id],
    queryFn: () => api.workouts.list(),
    enabled: !!athlete,
  });

  const pushMutation = useMutation({
    mutationFn: api.workouts.push,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["workouts", athlete?.id] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      name,
      structured_text,
      sport,
      press_lap,
    }: {
      id: string;
      name: string;
      structured_text: string;
      sport: Sport;
      press_lap: boolean;
    }) => api.workouts.update(id, { name, structured_text, sport, press_lap }),
    onSuccess: () => {
      setEditingId(null);
      void queryClient.invalidateQueries({ queryKey: ["workouts", athlete?.id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.workouts.delete,
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
            const isEditing = editingId === w.id;
            const phases = (w.llm_plan as { phases?: WorkoutPhase[] })?.phases;
            const maxDuration = phases?.length
              ? Math.max(...phases.map((p) => p.duration_min))
              : 0;

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
                      <label className="text-xs font-semibold text-text-muted">{t.settings.sport}</label>
                      <select
                        value={editSport}
                        onChange={(e) => setEditSport(e.target.value as Sport)}
                        className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
                      >
                        <option value="cycling">{t.settings.sports.cycling}</option>
                        <option value="running">{t.settings.sports.running}</option>
                        <option value="swimming">{t.settings.sports.swimming}</option>
                        <option value="cross_country_skiing">{t.settings.sports.cross_country_skiing}</option>
                        <option value="weight_training">{t.settings.sports.weight_training}</option>
                      </select>
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

                    <Checkbox
                      label={t.workouts.pressLap}
                      hint={t.workouts.pressLapHint}
                      checked={editPressLap}
                      onChange={setEditPressLap}
                    />

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
                            sport: editSport,
                            press_lap: editPressLap,
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
                        {w.workout_type ? ((t.coach.types as Record<string, string>)[w.workout_type] ?? w.workout_type) : ""}
                        {w.duration_seconds ? ` · ${formatDuration(w.duration_seconds)}` : ""}
                        {w.target_tss ? ` · TSS ${Math.round(w.target_tss)}` : ""}
                        {w.scheduled_date ? ` · ${formatDate(w.scheduled_date)}` : ""}
                      </p>
                    </div>
                    <Badge variant={w.status ? (statusVariant[w.status] ?? "default") : "default"}>
                      {w.status || ""}
                    </Badge>
                  </div>

                  {(w.structured_text || (phases && phases.length > 0) || w.llm_reasoning) && (
                    <button
                      type="button"
                      onClick={() => setExpanded(isOpen ? null : w.id)}
                      className="mt-2 flex items-center gap-1 text-xs text-text-muted transition-colors hover:text-text-secondary"
                    >
                      <ChevronDown
                        className={cn("h-3.5 w-3.5 transition-transform", isOpen && "rotate-180")}
                      />
                      {language === "de"
                        ? (isOpen ? "Details ausblenden" : "Details anzeigen")
                        : (isOpen ? "Hide details" : "Show details")}
                    </button>
                  )}
                  {isOpen && (
                    <div className="mt-4 space-y-4 border-t border-border/50 pt-4">
                      {phases && phases.length > 0 && (
                        <div className="space-y-2">
                          <h3 className="text-xs font-semibold text-text-secondary">
                            {t.coach.phases}
                          </h3>
                          <div className="space-y-1.5">
                            {phases.map((p, idx) => (
                              <PhaseBar key={idx} phase={p} maxDurationMin={maxDuration} />
                            ))}
                          </div>
                        </div>
                      )}

                      {w.structured_text && (
                        <div className="space-y-1">
                          <h3 className="text-xs font-semibold text-text-secondary">
                            Intervals.icu
                          </h3>
                          <CodeBlock code={w.structured_text} />
                        </div>
                      )}

                      {w.llm_reasoning && (
                        <div className="space-y-1">
                          <h3 className="text-xs font-semibold text-text-secondary">
                            {t.coach.reasoning}
                          </h3>
                          <p className="text-xs leading-relaxed text-text-muted">
                            {w.llm_reasoning}
                          </p>
                        </div>
                      )}

                      {w.coach_notes && (
                        <div className="space-y-1">
                          <h3 className="text-xs font-semibold text-text-secondary">
                            {t.coach.notes}
                          </h3>
                          <p className="text-xs leading-relaxed text-text-muted">
                            {w.coach_notes}
                          </p>
                        </div>
                      )}
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
                        setEditSport(w.sport);
                        setEditPressLap(w.press_lap ?? false);
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Bearbeiten
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-danger hover:text-danger hover:bg-danger/10"
                      loading={deleteMutation.isPending && deleteMutation.variables === w.id}
                      onClick={() => {
                        if (confirm("Möchtest du dieses Workout wirklich löschen?")) {
                          deleteMutation.mutate(w.id);
                        }
                      }}
                    >
                      <Trash className="h-3.5 w-3.5" />
                      Löschen
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
