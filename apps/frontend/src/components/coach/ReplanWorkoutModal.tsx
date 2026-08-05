"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Sparkles, X, AlertCircle, Calendar, Zap, CheckCircle2 } from "lucide-react";

import { api, API_BASE, csrfHeaders } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import type { Route, Sport, WeeklyPlan, Workout, WorkoutPhase } from "@/lib/types";
import type { CoachEvent } from "@/hooks/useCoachStream";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { Slider } from "@/components/ui/Slider";
import { WorkoutTypeSelector } from "@/components/coach/WorkoutTypeSelector";
import { StreamPanel } from "@/components/coach/StreamPanel";
import { LoadReflectionWidget } from "@/components/coach/LoadReflectionWidget";
import { PhaseBar } from "@/components/coach/PhaseBar";

interface ReplanWorkoutModalProps {
  workout: Workout | null;
  weeklyPlan: WeeklyPlan | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ReplanWorkoutModal({
  workout,
  weeklyPlan,
  isOpen,
  onClose,
  onSuccess,
}: ReplanWorkoutModalProps) {
  const athlete = useAthlete();
  const t = useT();

  const [workoutType, setWorkoutType] = useState<string>("threshold");
  const [sport, setSport] = useState<Sport>("cycling");
  const [loadPolicy, setLoadPolicy] = useState<"target" | "allow_exceed" | "allow_fall_below">("target");
  const [aggressiveness, setAggressiveness] = useState<number>(0);
  const [scheduledDate, setScheduledDate] = useState<string>("");
  const [routeId, setRouteId] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [provider, setProvider] = useState<string>("ollama");
  const [pressLap, setPressLap] = useState<boolean>(false);

  const [isStreaming, setIsStreaming] = useState(false);
  const [events, setEvents] = useState<CoachEvent[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [replannedResult, setReplannedResult] = useState<Workout | null>(null);
  const [phases, setPhases] = useState<WorkoutPhase[] | undefined>();
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const { data: routes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(),
    enabled: !!athlete && isOpen,
  });

  // Pre-fill form when workout changes
  useEffect(() => {
    if (workout) {
      setWorkoutType(workout.workout_type || "threshold");
      setSport(workout.sport || athlete?.sport || "cycling");
      setLoadPolicy("target"); // Standard is target load
      setAggressiveness(0);
      setScheduledDate(workout.scheduled_date ? String(workout.scheduled_date) : "");
      setRouteId(workout.route_id || "");
      setNotes(workout.coach_notes || "");
      setPressLap(workout.press_lap ?? false);
      setEvents([]);
      setStreamError(null);
      setReplannedResult(null);
      setPhases(undefined);
    }
  }, [workout, athlete, isOpen]);

  if (!isOpen || !workout || !weeklyPlan) return null;

  async function handleReplan(e: React.FormEvent) {
    e.preventDefault();
    if (!athlete || !workout || !weeklyPlan) return;

    abortController?.abort();
    const controller = new AbortController();
    setAbortController(controller);

    setIsStreaming(true);
    setEvents([]);
    setStreamError(null);
    setReplannedResult(null);

    const body = {
      workout_type: workoutType,
      sport: sport,
      aggressiveness: aggressiveness,
      load_policy: loadPolicy,
      scheduled_date: scheduledDate || undefined,
      route_id: routeId || undefined,
      notes: notes || undefined,
      provider: provider,
      press_lap: pressLap,
      weekly_plan_id: weeklyPlan.id,
      source_workout_id: workout.id,
    };

    try {
      let res = await fetch(`${API_BASE}/coach/generate`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (res.status === 401) {
        const refreshed = await api.auth.refresh().then(() => true).catch(() => false);
        if (refreshed) {
          res = await fetch(`${API_BASE}/coach/generate`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json", ...csrfHeaders() },
            body: JSON.stringify(body),
            signal: controller.signal,
          });
        }
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Replan generation failed" }));
        setStreamError(err.detail ?? "Failed to initialize stream");
        setIsStreaming(false);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buffer = "";

      const processBlock = (block: string) => {
        let eventType = "";
        let dataRaw = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) eventType = line.slice(6).trim();
          else if (line.startsWith("data:")) dataRaw += line.slice(5).trim();
        }
        if (!eventType) return;

        let parsedData: any = dataRaw;
        try {
          parsedData = JSON.parse(dataRaw);
        } catch {}

        if (eventType === "thinking") {
          setEvents((s) => [...s, { kind: "thinking", text: String(parsedData) }]);
        } else if (eventType === "tool_call") {
          setEvents((s) => [...s, { kind: "tool_call", text: String(parsedData) }]);
        } else if (eventType === "tool_result") {
          setEvents((s) => [...s, { kind: "tool_result", text: String(parsedData) }]);
        } else if (eventType === "error") {
          setStreamError(String(parsedData));
          setIsStreaming(false);
        } else if (eventType === "workout_plan") {
          const planMeta = parsedData as { workout_id: string };
          api.workouts.get(planMeta.workout_id).then((fullWorkout) => {
            setReplannedResult(fullWorkout);
            const p = (fullWorkout.llm_plan as { phases?: WorkoutPhase[] })?.phases;
            if (Array.isArray(p)) setPhases(p);
            onSuccess();
          });
          setIsStreaming(false);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          if (block.trim()) processBlock(block);
        }
      }
      if (buffer.trim()) processBlock(buffer);
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setStreamError((err as Error).message);
      }
    } finally {
      setIsStreaming(false);
    }
  }

  function handleStop() {
    abortController?.abort();
    setIsStreaming(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-3xl rounded-2xl bg-surface border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border/80 bg-surface-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-accent/15 text-accent border border-accent/20">
              <RefreshCw className="h-4.5 w-4.5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text">Training mit AI neu planen</h2>
              <p className="text-xs text-text-muted">
                KW {weeklyPlan.start_date} • {workout.name} ({workout.sport})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5 overflow-y-auto flex-1">
          <form onSubmit={handleReplan} className="space-y-4">
            {/* Workout Goal / Type (Kept from original workout) */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-medium text-text-secondary">
                  Trainingsziel & Fokustyp (beibehalten / anpassen)
                </span>
                <span className="text-[11px] text-accent font-semibold">
                  Original: {workout.workout_type}
                </span>
              </div>
              <WorkoutTypeSelector value={workoutType} onChange={setWorkoutType} />
            </div>

            {/* Load Constraint & Aggressiveness */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="Belastungssteuerung / Load Constraint"
                value={loadPolicy}
                onChange={(e) => setLoadPolicy(e.target.value as any)}
              >
                <option value="target">Zielbelastung einhalten (Standard - Wochentargets beachten)</option>
                <option value="allow_exceed">Überlastung erlaubt (Overreach / Maximaler Reiz)</option>
                <option value="allow_fall_below">Unterbelastung erlaubt (Regeneration / Erholung)</option>
              </Select>

              <Slider
                label="Trainingsbelastung / Aggressivität"
                hint="Variationsgrad der Ziel-Intensität (-2 bis +2)"
                value={aggressiveness}
                onChange={setAggressiveness}
              />
            </div>

            {/* Live Load Reflection Widget */}
            <LoadReflectionWidget
              scheduledDate={scheduledDate}
              selectedWeeklyPlan={weeklyPlan}
              selectedWorkout={workout}
              loadPolicy={loadPolicy}
              aggressiveness={aggressiveness}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Select
                label={t.settings.sport}
                value={sport}
                onChange={(e) => setSport(e.target.value as Sport)}
              >
                <option value="cycling">{t.settings.sports.cycling}</option>
                <option value="running">{t.settings.sports.running}</option>
                <option value="swimming">{t.settings.sports.swimming}</option>
                <option value="cross_country_skiing">{t.settings.sports.cross_country_skiing}</option>
                <option value="weight_training">{t.settings.sports.weight_training}</option>
              </Select>

              <Select
                label={t.coach.modelProvider}
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="ollama">{t.coach.providers.ollama}</option>
                <option value="gemini">{t.coach.providers.gemini}</option>
              </Select>

              <Input
                label={t.coach.date}
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
              />
            </div>

            {routes && routes.length > 0 && (
              <Select
                label={`${t.coach.route} (${t.common.optional})`}
                value={routeId}
                onChange={(e) => setRouteId(e.target.value)}
              >
                <option value="">{t.coach.noRoute}</option>
                {routes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({(r.distance_m / 1000).toFixed(0)} km, {Math.round(r.elevation_gain_m)} hm)
                  </option>
                ))}
              </Select>
            )}

            <Textarea
              label="Zusätzliche Coach-Hinweise für die Neuplanung (optional)"
              placeholder="Z. B. 'Fühle mich heute etwas müde' oder 'Fokus auf hohe Trittfrequenz'..."
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />

            <Checkbox
              label={t.workouts.pressLap}
              hint={t.workouts.pressLapHint}
              checked={pressLap}
              onChange={setPressLap}
            />

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} disabled={isStreaming}>
                Abbrechen
              </Button>
              <Button type="submit" loading={isStreaming} disabled={isStreaming}>
                {isStreaming ? "Coach plant neu..." : "Neu generieren & Speichern"}
              </Button>
              {isStreaming && (
                <Button type="button" variant="ghost" onClick={handleStop}>
                  Stoppen
                </Button>
              )}
            </div>
          </form>

          {/* Streaming & Results */}
          {(events.length > 0 || isStreaming) && (
            <Card>
              <CardHeader className="py-2.5">
                <CardTitle className="text-xs font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-accent" /> Der AI Coach replant dieses Training...
                  </span>
                </CardTitle>
              </CardHeader>
              <CardBody className="py-3">
                <StreamPanel events={events} isStreaming={isStreaming} />
              </CardBody>
            </Card>
          )}

          {streamError && (
            <div className="bg-danger/10 border border-danger/20 text-danger text-xs rounded-lg p-3 flex gap-2 items-center">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{streamError}</span>
            </div>
          )}

          {replannedResult && (
            <div className="bg-accent/10 border border-accent/30 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-accent font-bold text-sm">
                  <CheckCircle2 className="h-4.5 w-4.5" />
                  <span>Einzeltraining erfolgreich im Wochenplan aktualisiert!</span>
                </div>
                <Button size="sm" variant="primary" onClick={onClose}>
                  Fertig
                </Button>
              </div>

              <div className="text-xs text-text space-y-2 pt-1 border-t border-accent/20">
                <div className="font-bold text-sm text-text">{replannedResult.name}</div>
                <div className="flex gap-3 text-text-muted tabular-nums">
                  <span>Dauer: <strong>{Math.round((replannedResult.duration_seconds ?? 0) / 60)} min</strong></span>
                  <span>TSS: <strong>{Math.round(replannedResult.target_tss ?? 0)}</strong></span>
                  <span className="capitalize">{replannedResult.workout_type}</span>
                </div>

                {phases && phases.length > 0 && (
                  <div className="space-y-1 pt-1">
                    {phases.map((p, i) => (
                      <PhaseBar key={i} phase={p} maxDurationMin={Math.max(...phases.map((x) => x.duration_min))} />
                    ))}
                  </div>
                )}

                {replannedResult.llm_reasoning && (
                  <div className="bg-surface/80 p-2.5 rounded-lg border border-border/50 text-xs text-text-muted">
                    <strong className="text-text block mb-0.5">Neuplanungs-Begründung des Coaches:</strong>
                    {replannedResult.llm_reasoning}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
