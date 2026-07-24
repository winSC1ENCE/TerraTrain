"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useCoachStream } from "@/hooks/useCoachStream";
import { useT } from "@/lib/i18n";
import type { Sport, WorkoutPhase } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { StreamPanel } from "@/components/coach/StreamPanel";
import { WorkoutPlanCard } from "@/components/coach/WorkoutPlanCard";
import { WorkoutTypeSelector } from "@/components/coach/WorkoutTypeSelector";

import { Slider } from "@/components/ui/Slider";

export default function CoachPage() {
  const athlete = useAthlete();
  const t = useT();
  const { events, plan, error, isStreaming, start, stop } = useCoachStream();

  const [sport, setSport] = useState<Sport>(athlete?.sport ?? "cycling");
  const [aggressiveness, setAggressiveness] = useState<number>(0);
  const [workoutType, setWorkoutType] = useState("threshold");
  const [scheduledDate, setScheduledDate] = useState("");
  const [routeId, setRouteId] = useState("");
  const [notes, setNotes] = useState("");
  const [phases, setPhases] = useState<WorkoutPhase[] | undefined>();
  const [provider, setProvider] = useState("ollama");
  const [pressLap, setPressLap] = useState(false);

  const { data: routes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(),
    enabled: !!athlete,
  });

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
      scheduled_date: scheduledDate || undefined,
      route_id: routeId || undefined,
      notes: notes || undefined,
      provider: provider,
      press_lap: pressLap,
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">{t.coach.title}</h1>
        <p className="mt-0.5 text-sm text-text-muted">{t.coach.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Form */}
        <Card>
          <CardBody className="pt-5">
            <form onSubmit={handleSubmit} className="space-y-4">
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

              <Slider
                label="Trainingsbelastung / Aggressivität"
                hint="Steuert die Ziel-Intensität/TSS (0 = Ausgewogen / Normal wie bisher, +1/+2 = Intensiver / Mehr Belastung, -1/-2 = Leichter / Konservativ)"
                value={aggressiveness}
                onChange={setAggressiveness}
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
                  {isStreaming ? t.coach.generating : t.coach.generate}
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
