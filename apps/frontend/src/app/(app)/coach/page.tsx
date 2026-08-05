"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, Calendar, Layers, PlusCircle, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useCoachStream } from "@/hooks/useCoachStream";
import { useT } from "@/lib/i18n";
import type { Route, Sport, WeeklyPlan, Workout, WorkoutPhase } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { StreamPanel } from "@/components/coach/StreamPanel";
import { WorkoutPlanCard } from "@/components/coach/WorkoutPlanCard";
import { WorkoutTypeSelector } from "@/components/coach/WorkoutTypeSelector";
import { Slider } from "@/components/ui/Slider";
import { GpxDropzone } from "@/components/coach/GpxDropzone";
import { LoadReflectionWidget } from "@/components/coach/LoadReflectionWidget";

export default function CoachPage() {
  const athlete = useAthlete();
  const t = useT();
  const { events, plan, error, isStreaming, start, stop } = useCoachStream();

  // Mode: "clean" (Neues Workout) vs "recreate" (Einzeltraining aus Wochenplan neu erstellen)
  const [plannerMode, setPlannerMode] = useState<"clean" | "recreate">("clean");

  const [sport, setSport] = useState<Sport>(athlete?.sport ?? "cycling");
  const [aggressiveness, setAggressiveness] = useState<number>(0);
  const [loadPolicy, setLoadPolicy] = useState<"target" | "allow_exceed" | "allow_fall_below">("target");
  const [workoutType, setWorkoutType] = useState("threshold");
  const [scheduledDate, setScheduledDate] = useState("");
  const [routeId, setRouteId] = useState("");
  const [notes, setNotes] = useState("");
  const [phases, setPhases] = useState<WorkoutPhase[] | undefined>();
  const [provider, setProvider] = useState("ollama");
  const [pressLap, setPressLap] = useState(false);

  // Recreate from weekly plan state
  const [selectedWeeklyPlanId, setSelectedWeeklyPlanId] = useState<string>("");
  const [selectedWorkoutId, setSelectedWorkoutId] = useState<string>("");

  const { data: routes, refetch: refetchRoutes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(),
    enabled: !!athlete,
  });

  const { data: weeklyPlans } = useQuery({
    queryKey: ["weeklyPlans", athlete?.id],
    queryFn: () => api.weeklyPlans.list(),
    enabled: !!athlete,
  });

  const selectedWeeklyPlan = weeklyPlans?.find((p) => p.id === selectedWeeklyPlanId);
  const selectedWorkout = selectedWeeklyPlan?.workouts.find((w) => w.id === selectedWorkoutId);
  const currentRoute = routes?.find((r) => r.id === routeId);

  // Pre-fill form when a workout from a weekly plan is selected
  useEffect(() => {
    if (plannerMode === "recreate" && selectedWorkout) {
      setSport(selectedWorkout.sport || athlete?.sport || "cycling");
      setWorkoutType(selectedWorkout.workout_type || "threshold");
      if (selectedWorkout.scheduled_date) {
        setScheduledDate(String(selectedWorkout.scheduled_date));
      }
      if (selectedWorkout.route_id) {
        setRouteId(selectedWorkout.route_id);
      }
      if (selectedWorkout.press_lap !== undefined) {
        setPressLap(selectedWorkout.press_lap);
      }
      if (selectedWorkout.coach_notes) {
        setNotes(selectedWorkout.coach_notes);
      }
    }
  }, [plannerMode, selectedWorkout, athlete]);

  // After a plan arrives, load the persisted workout for its phase breakdown
  useEffect(() => {
    if (!plan) {
      setPhases(undefined);
      return;
    }
    api.workouts
      .get(plan.workout_id)
      .then((w) => {
        const p = (w.llm_plan as { phases?: WorkoutPhase[] })?.phases;
        if (Array.isArray(p)) setPhases(p);
      })
      .catch(() => setPhases(undefined));
  }, [plan]);

  if (!athlete) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!athlete) return;
    start({
      workout_type: workoutType,
      sport: sport,
      aggressiveness: aggressiveness,
      load_policy: loadPolicy,
      scheduled_date: scheduledDate || undefined,
      route_id: routeId || undefined,
      notes: notes || undefined,
      provider: provider,
      press_lap: pressLap,
      weekly_plan_id: plannerMode === "recreate" && selectedWeeklyPlanId ? selectedWeeklyPlanId : undefined,
      source_workout_id: plannerMode === "recreate" && selectedWorkoutId ? selectedWorkoutId : undefined,
    });
  }

  function handleRouteUploaded(newRoute: Route) {
    refetchRoutes();
    setRouteId(newRoute.id);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">{t.coach.title}</h1>
          <p className="mt-0.5 text-sm text-text-muted">{t.coach.subtitle}</p>
        </div>

        {/* Mode Selector */}
        <div className="inline-flex rounded-xl bg-background-card p-1 border border-border-muted">
          <button
            type="button"
            onClick={() => {
              setPlannerMode("clean");
              setSelectedWeeklyPlanId("");
              setSelectedWorkoutId("");
            }}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              plannerMode === "clean"
                ? "bg-primary text-white shadow-sm"
                : "text-text-muted hover:text-text-primary"
            }`}
          >
            <PlusCircle className="h-3.5 w-3.5" />
            Clean New Session
          </button>
          <button
            type="button"
            onClick={() => setPlannerMode("recreate")}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
              plannerMode === "recreate"
                ? "bg-primary text-white shadow-sm"
                : "text-text-muted hover:text-text-primary"
            }`}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Recreate from Weekly Plan
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Form */}
        <Card>
          <CardBody className="pt-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Recreate from Weekly Plan selector */}
              {plannerMode === "recreate" && (
                <div className="rounded-xl border border-primary/30 bg-primary/5 p-3.5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                    <Calendar className="h-4 w-4" />
                    <span>Wochenplan & Einzeltraining auswählen</span>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <Select
                      label="Wochenplan"
                      value={selectedWeeklyPlanId}
                      onChange={(e) => {
                        setSelectedWeeklyPlanId(e.target.value);
                        setSelectedWorkoutId("");
                      }}
                    >
                      <option value="">-- Wochenplan wählen --</option>
                      {weeklyPlans?.map((wp) => (
                        <option key={wp.id} value={wp.id}>
                          KW {wp.start_date} ({(wp.week_type || "Plan").toUpperCase()}, {wp.target_tss} TSS)
                        </option>
                      ))}
                    </Select>

                    <Select
                      label="Session / Training"
                      disabled={!selectedWeeklyPlanId}
                      value={selectedWorkoutId}
                      onChange={(e) => setSelectedWorkoutId(e.target.value)}
                    >
                      <option value="">-- Trainingseinheit wählen --</option>
                      {selectedWeeklyPlan?.workouts.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name} ({w.sport}, {w.scheduled_date || "Kein Datum"})
                        </option>
                      ))}
                    </Select>
                  </div>
                </div>
              )}

              <div>
                <span className="mb-1.5 block text-xs font-medium text-text-secondary">
                  {t.coach.workoutType}
                </span>
                <WorkoutTypeSelector value={workoutType} onChange={setWorkoutType} />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
                <Select
                  label={`${t.coach.route} (${t.common.optional})`}
                  value={routeId}
                  onChange={(e) => setRouteId(e.target.value)}
                >
                  <option value="">{t.coach.noRoute}</option>
                  {routes?.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({(r.distance_m / 1000).toFixed(0)} km,{" "}
                      {Math.round(r.elevation_gain_m)} hm)
                    </option>
                  ))}
                </Select>
              </div>

              {/* Direct GPX Dropzone */}
              <GpxDropzone
                sport={sport}
                onRouteUploaded={handleRouteUploaded}
                selectedRoute={currentRoute}
              />

              {/* Load Override & Aggressiveness */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Select
                  label="Belastungssteuerung / Load Constraint"
                  value={loadPolicy}
                  onChange={(e) => setLoadPolicy(e.target.value as any)}
                >
                  <option value="target">Zielbelastung einhalten (Standard)</option>
                  <option value="allow_exceed">Überlastung erlaubt (Overreach / Pushing)</option>
                  <option value="allow_fall_below">Unterbelastung erlaubt (Recovery / Reduktion)</option>
                </Select>

                <Slider
                  label="Trainingsbelastung / Aggressivität"
                  hint="Variationsgrad der Ziel-Intensität"
                  value={aggressiveness}
                  onChange={setAggressiveness}
                />
              </div>

              {/* Live Load Reflection Widget */}
              <LoadReflectionWidget
                scheduledDate={scheduledDate}
                selectedWeeklyPlan={selectedWeeklyPlan}
                selectedWorkout={selectedWorkout}
                loadPolicy={loadPolicy}
                aggressiveness={aggressiveness}
              />

              <Textarea
                label={`${t.coach.notes} (${t.common.optional})`}
                placeholder={t.coach.notesPlaceholder}
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />

              <Checkbox
                label={t.workouts.pressLap}
                hint={t.workouts.pressLapHint}
                checked={pressLap}
                onChange={setPressLap}
              />

              <div className="flex gap-2">
                <Button type="submit" loading={isStreaming}>
                  {isStreaming
                    ? t.coach.generating
                    : plannerMode === "recreate"
                    ? "Einzeltraining neu erstellen"
                    : t.coach.generate}
                </Button>
                {isStreaming && (
                  <Button type="button" variant="ghost" onClick={stop}>
                    {t.coach.stop}
                  </Button>
                )}
              </div>
            </form>
          </CardBody>
        </Card>

        {/* Stream + result */}
        <div className="space-y-4">
          {(events.length > 0 || isStreaming) && (
            <Card>
              <CardHeader>
                <CardTitle>{t.coach.thinking}</CardTitle>
              </CardHeader>
              <CardBody>
                <StreamPanel events={events} isStreaming={isStreaming} />
              </CardBody>
            </Card>
          )}

          {error && (
            <Card className="border-danger/40">
              <CardBody className="pt-5">
                <p className="text-sm text-danger">{error}</p>
              </CardBody>
            </Card>
          )}

          {plan && <WorkoutPlanCard plan={plan} phases={phases} />}
        </div>
      </div>
    </div>
  );
}
