"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  MapPin,
  Pencil,
  Plus,
  Send,
  Sparkles,
  Trash,
} from "lucide-react";

import { api, API_BASE } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import type { Route, Workout, WorkoutPhase } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { StreamPanel } from "@/components/coach/StreamPanel";
import { PhaseBar } from "@/components/coach/PhaseBar";

interface ScheduleItem {
  id: string;
  day_of_week: number;
  duration_min: number;
  route_id: string;
  notes: string;
}

const DAYS_OF_WEEK = [
  "Montag",
  "Dienstag",
  "Mittwoch",
  "Donnerstag",
  "Freitag",
  "Samstag",
  "Sonntag",
];

const EN_DAYS_OF_WEEK = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function getNextMonday() {
  const d = new Date();
  const day = d.getDay();
  const diff = day === 0 ? 1 : 8 - day;
  d.setDate(d.getDate() + diff);
  return d.toISOString().split("T")[0];
}

export default function WeeklyPlannerPage() {
  const athlete = useAthlete();
  const t = useT();

  const [startDate, setStartDate] = useState(getNextMonday());
  const [mesocycleType, setMesocycleType] = useState("3-1");
  const [weekType, setWeekType] = useState("load_1");
  const [globalNotes, setGlobalNotes] = useState("");
  const [provider, setProvider] = useState("ollama");

  // Day schedules setup
  const [schedules, setSchedules] = useState<ScheduleItem[]>(() => [
    { id: "1", day_of_week: 1, duration_min: 90, route_id: "", notes: "" },
    { id: "3", day_of_week: 3, duration_min: 90, route_id: "", notes: "" },
    { id: "5", day_of_week: 5, duration_min: 120, route_id: "", notes: "" },
    { id: "6", day_of_week: 6, duration_min: 90, route_id: "", notes: "" },
  ]);

  // Detection states
  const [detection, setDetection] = useState<{
    history: Array<{ week_label: string; start_date: string; end_date: string; tss: number }>;
    recommended_week_type: string;
    reasoning: string;
  } | null>(null);
  const [detectLoading, setDetectLoading] = useState(false);

  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [events, setEvents] = useState<Array<{ kind: "thinking" | "tool_call" | "tool_result"; text: string }>>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // Persisted plan details
  const [generatedPlan, setGeneratedPlan] = useState<{
    id: string;
    mesocycle_type: string;
    week_type: string;
    coach_rationale: string;
    workouts: Workout[];
  } | null>(null);

  // Expanded workouts
  const [expandedWorkouts, setExpandedWorkouts] = useState<Record<string, boolean>>({});
  // Editing state for workouts
  const [editingWorkout, setEditingWorkout] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editStructuredText, setEditStructuredText] = useState("");
  const [savingWorkout, setSavingWorkout] = useState(false);
  const [pushingAll, setPushingAll] = useState(false);

  // Fetch routes
  const { data: routes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(athlete!.id),
    enabled: !!athlete,
  });

  // Query mesocycle detection
  useEffect(() => {
    if (!athlete || !startDate) return;
    setDetectLoading(true);
    api.weeklyPlans
      .detect(athlete.id, startDate, mesocycleType)
      .then((res) => {
        setDetection(res);
        setWeekType(res.recommended_week_type);
      })
      .catch((err) => {
        console.error("Mesocycle detection failed", err);
      })
      .finally(() => {
        setDetectLoading(false);
      });
  }, [athlete, startDate, mesocycleType]);

  if (!athlete) return null;

  const activeDays = schedules;

  const addSession = (dayIndex: number) => {
    const newItem: ScheduleItem = {
      id: Math.random().toString(36).substring(2, 9),
      day_of_week: dayIndex,
      duration_min: 90,
      route_id: "",
      notes: "",
    };
    setSchedules((prev) => [...prev, newItem]);
  };

  const deleteSession = (id: string) => {
    setSchedules((prev) => prev.filter((item) => item.id !== id));
  };

  const updateSession = (id: string, fields: Partial<ScheduleItem>) => {
    setSchedules((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...fields } : item))
    );
  };

  // SSE Generator Stream
  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!athlete || activeDays.length === 0) return;

    abortController?.abort();
    const controller = new AbortController();
    setAbortController(controller);

    setIsStreaming(true);
    setEvents([]);
    setStreamError(null);
    setGeneratedPlan(null);

    const body = {
      athlete_id: athlete.id,
      start_date: startDate,
      mesocycle_type: mesocycleType,
      week_type: weekType,
      schedules: activeDays.map((s) => ({
        day_of_week: s.day_of_week,
        duration_min: s.duration_min,
        route_id: s.route_id || null,
        notes: s.notes || null,
      })),
      notes: globalNotes || null,
      provider: provider,
    };

    try {
      const res = await fetch(`${API_BASE}/api/v1/weekly-plans/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Weekly planning failed" }));
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
        } else if (eventType === "weekly_plan") {
          const planMeta = parsedData as { weekly_plan_id: string };
          // Load fully populated weekly plan from backend
          api.weeklyPlans.get(planMeta.weekly_plan_id).then((fullPlan) => {
            setGeneratedPlan(fullPlan);
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

  async function handleDeletePlan() {
    if (!generatedPlan) return;
    if (!confirm("Möchtest du diesen Wochenplan und alle zugehörigen Workouts wirklich löschen?")) return;

    try {
      await api.weeklyPlans.delete(generatedPlan.id);
      setGeneratedPlan(null);
      setEvents([]);
    } catch (err) {
      alert((err as Error).message);
    }
  }

  async function handlePushAll() {
    if (!generatedPlan) return;
    setPushingAll(true);
    try {
      const res = await api.weeklyPlans.push(generatedPlan.id);
      // Reload weekly plan workouts to show updated statuses
      const fullPlan = await api.weeklyPlans.get(generatedPlan.id);
      setGeneratedPlan(fullPlan);
      alert(`Erfolgreich ${res.pushed_workout_ids.length} Workouts an Intervals.icu übertragen!`);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setPushingAll(false);
    }
  }

  async function handlePushSingle(workoutId: string) {
    try {
      await api.workouts.push(workoutId);
      if (generatedPlan) {
        const fullPlan = await api.weeklyPlans.get(generatedPlan.id);
        setGeneratedPlan(fullPlan);
      }
    } catch (err) {
      alert((err as Error).message);
    }
  }

  function startEditWorkout(w: Workout) {
    setEditingWorkout(w.id);
    setEditName(w.name);
    setEditStructuredText(w.structured_text ?? "");
  }

  async function handleSaveWorkout() {
    if (!editingWorkout || !generatedPlan) return;
    setSavingWorkout(true);
    try {
      await api.workouts.update(editingWorkout, {
        name: editName,
        structured_text: editStructuredText,
      });
      const fullPlan = await api.weeklyPlans.get(generatedPlan.id);
      setGeneratedPlan(fullPlan);
      setEditingWorkout(null);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setSavingWorkout(false);
    }
  }

  const toggleWorkoutExpand = (id: string) => {
    setExpandedWorkouts((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <div>
        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <Calendar className="h-5 w-5 text-accent" />
          {t.nav.weeklyPlanner}
        </h1>
        <p className="mt-0.5 text-sm text-text-muted">
          Plane deine gesamte Woche mit Mesozyklus-Periodisierung.
        </p>
      </div>

      {!generatedPlan && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Settings Panel */}
          <div className="lg:col-span-4 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Sparkles className="h-4.5 w-4.5 text-accent" /> Periodisierung
                </CardTitle>
              </CardHeader>
              <CardBody className="space-y-4 pt-1">
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Startdatum (Mo)"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                  <Select
                    label="Periodisierung"
                    value={mesocycleType}
                    onChange={(e) => setMesocycleType(e.target.value)}
                  >
                    <option value="3-1">3:1 Zyklus</option>
                    <option value="2-1">2:1 Zyklus</option>
                  </Select>
                </div>

                {/* Auto detection section */}
                <div className="bg-surface-2 rounded-lg p-3 border border-border/50 text-xs space-y-2">
                  <div className="font-semibold text-text flex items-center justify-between">
                    <span>Meso-Erkennung (Intervals.icu)</span>
                    {detectLoading && <span className="animate-pulse text-accent">Lädt...</span>}
                  </div>
                  {detection && !detectLoading ? (
                    <>
                      <div className="flex gap-2 items-center overflow-x-auto pb-1 mt-1.5 scrollbar-thin">
                        {detection.history.map((h, i) => (
                          <div
                            key={i}
                            className="bg-surface border border-border/70 rounded px-2 py-1 text-center min-w-[70px]"
                          >
                            <div className="text-[10px] text-text-muted">{h.week_label}</div>
                            <div className="font-bold text-text tabular-nums">{Math.round(h.tss)}</div>
                            <div className="text-[9px] text-text-muted">TSS</div>
                          </div>
                        ))}
                      </div>
                      <div className="text-text-muted mt-1 leading-relaxed">
                        <strong className="text-accent">Empfehlung:</strong> {detection.reasoning}
                      </div>
                    </>
                  ) : (
                    <p className="text-text-muted">TSS-Historie der letzten 4 Wochen wird geladen...</p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <Select
                    label="Wochen-Typ"
                    value={weekType}
                    onChange={(e) => setWeekType(e.target.value)}
                  >
                    <option value="load_1">Belastungswoche 1</option>
                    <option value="load_2">Belastungswoche 2</option>
                    {mesocycleType === "3-1" && <option value="load_3">Belastungswoche 3</option>}
                    <option value="recovery">Erholungswoche</option>
                  </Select>

                  <Select
                    label="Modell-Anbieter"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                  >
                    <option value="ollama">Ollama (Lokal)</option>
                    <option value="gemini">Gemini (Cloud)</option>
                  </Select>
                </div>

                <Textarea
                  label="Globale Coach-Hinweise (optional)"
                  placeholder="Z. B. 'Fokus auf Klettern' oder 'Bin leicht erkältet'..."
                  rows={2}
                  value={globalNotes}
                  onChange={(e) => setGlobalNotes(e.target.value)}
                />

                <form onSubmit={handleGenerate}>
                  <Button
                    type="submit"
                    className="w-full mt-2"
                    loading={isStreaming}
                    disabled={activeDays.length === 0}
                  >
                    {isStreaming ? "Woche wird geplant..." : "Wochenplan erstellen"}
                  </Button>
                </form>
              </CardBody>
            </Card>

            {/* Stream panel */}
            {(events.length > 0 || isStreaming) && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-semibold">{t.coach.thinking}</CardTitle>
                  {isStreaming && (
                    <Button variant="ghost" size="sm" onClick={handleStop} className="text-xs text-danger h-7 px-2">
                      Abbrechen
                    </Button>
                  )}
                </CardHeader>
                <CardBody className="max-h-[350px] overflow-y-auto pt-1">
                  <StreamPanel events={events} isStreaming={isStreaming} />
                </CardBody>
              </Card>
            )}

            {streamError && (
              <Card className="border-danger/40 bg-danger/5">
                <CardBody className="flex gap-3 text-xs text-danger py-3">
                  <AlertCircle className="h-5 w-5 shrink-0" />
                  <div>
                    <span className="font-semibold">Fehler beim Generieren:</span>
                    <p className="mt-1 leading-relaxed">{streamError}</p>
                  </div>
                </CardBody>
              </Card>
            )}
          </div>

          {/* Daily Schedule Panel */}
          <div className="lg:col-span-8">
            <Card className="h-full">
              <CardHeader className="border-b border-border/70 pb-3">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Activity className="h-4.5 w-4.5 text-accent" />
                  Wochenplaner-Kalender ({activeDays.length} Trainingseinheiten)
                </CardTitle>
              </CardHeader>
              <CardBody className="p-0 divide-y divide-border/60">
                {DAYS_OF_WEEK.map((dayName, dayIdx) => {
                  const daySchedules = schedules.filter((s) => s.day_of_week === dayIdx);
                  return (
                    <div
                      key={dayIdx}
                      className={`p-4 transition-colors ${
                        daySchedules.length > 0 ? "bg-surface-2/30" : "bg-bg/10"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4 mb-2">
                        <span className="text-sm font-bold text-text">
                          {dayName}
                        </span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => addSession(dayIdx)}
                          className="text-xs text-accent h-7 px-2"
                        >
                          <Plus className="h-3.5 w-3.5 mr-1" /> Einheit hinzufügen
                        </Button>
                      </div>

                      {daySchedules.length > 0 ? (
                        <div className="space-y-3 pl-3 border-l-2 border-accent/20">
                          {daySchedules.map((day, sIdx) => (
                            <div key={day.id} className="flex flex-wrap items-center gap-3 w-full">
                              {daySchedules.length > 1 && (
                                <span className="text-[10px] bg-accent/15 text-accent font-bold px-1.5 py-0.5 rounded">
                                  Einheit {sIdx + 1}
                                </span>
                              )}

                              {/* Duration */}
                              <div className="w-24">
                                <label className="text-[10px] uppercase tracking-wider text-text-muted font-bold block mb-1">
                                  Dauer (min)
                                </label>
                                <input
                                  type="number"
                                  min="10"
                                  max="600"
                                  value={day.duration_min}
                                  onChange={(e) =>
                                    updateSession(day.id, {
                                      duration_min: Math.max(10, parseInt(e.target.value) || 0),
                                    })
                                  }
                                  className="w-full px-2 py-1 text-sm bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent text-center tabular-nums"
                                />
                              </div>

                              {/* Route Selection */}
                              <div className="w-48">
                                <label className="text-[10px] uppercase tracking-wider text-text-muted font-bold block mb-1">
                                  Route (optional)
                                </label>
                                <select
                                  value={day.route_id}
                                  onChange={(e) =>
                                    updateSession(day.id, { route_id: e.target.value })
                                  }
                                  className="w-full px-2 py-1 text-sm bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
                                >
                                  <option value="">{t.coach.noRoute}</option>
                                  {routes?.map((r) => (
                                    <option key={r.id} value={r.id}>
                                      {r.name} ({(r.distance_m / 1000).toFixed(0)} km)
                                    </option>
                                  ))}
                                </select>
                              </div>

                              {/* Day notes */}
                              <div className="flex-1 min-w-[180px]">
                                <label className="text-[10px] uppercase tracking-wider text-text-muted font-bold block mb-1">
                                  Notizen
                                </label>
                                <input
                                  type="text"
                                  placeholder="Z. B. 'Nur lockeres Flachland'..."
                                  value={day.notes}
                                  onChange={(e) =>
                                    updateSession(day.id, { notes: e.target.value })
                                  }
                                  className="w-full px-3 py-1 text-sm bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
                                />
                              </div>

                              {/* Delete button */}
                              <div className="pt-5">
                                <button
                                  type="button"
                                  onClick={() => deleteSession(day.id)}
                                  className="p-1.5 text-text-muted hover:text-danger hover:bg-danger/10 rounded transition-colors"
                                >
                                  <Trash className="h-4 w-4" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-text-muted italic pl-3">Ruhetag / Rest Day</div>
                      )}
                    </div>
                  );
                })}
              </CardBody>
            </Card>
          </div>
        </div>
      )}

      {/* Generated Weekly Plan Display */}
      {generatedPlan && (
        <div className="space-y-6">
          <Card className="border-accent/40 bg-accent/5">
            <CardHeader className="flex flex-row items-start justify-between">
              <div>
                <CardTitle sub="Erstellter Trainingsplan">
                  Woche ab Montag, {new Date(startDate).toLocaleDateString()}
                </CardTitle>
                <div className="flex gap-4 text-xs text-text-muted mt-2 tabular-nums">
                  <span>
                    Mesozykus: <strong className="text-text">{generatedPlan.mesocycle_type}</strong>
                  </span>
                  <span>
                    Wochentyp:{" "}
                    <strong className="text-text">
                      {generatedPlan.week_type === "recovery"
                        ? "Erholung"
                        : `Belastung (Woche ${generatedPlan.week_type.split("_")[1]})`}
                    </strong>
                  </span>
                  <span>
                    Einheiten: <strong className="text-text">{generatedPlan.workouts.length}</strong>
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="danger" size="sm" onClick={handleDeletePlan}>
                  Plan löschen
                </Button>
                <Button size="sm" onClick={handlePushAll} loading={pushingAll}>
                  Ganze Woche übertragen
                </Button>
              </div>
            </CardHeader>
            <CardBody className="pt-2">
              <h4 className="text-xs font-semibold text-text-secondary mb-1">Periodisierungs-Begründung des Coaches</h4>
              <p className="text-xs leading-relaxed text-text-muted">{generatedPlan.coach_rationale}</p>
            </CardBody>
          </Card>

          {/* List of days */}
          <div className="space-y-4">
            {DAYS_OF_WEEK.map((dayName, idx) => {
              // Find workout for this day_of_week
              const workout = generatedPlan.workouts.find((w) => {
                const wDate = new Date(w.scheduled_date!);
                // Check if workout scheduled_date falls on this index (Monday = 0)
                const startDt = new Date(startDate);
                const diffDays = Math.round((wDate.getTime() - startDt.getTime()) / (1000 * 3600 * 24));
                return diffDays === idx;
              });

              if (!workout) {
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-surface/50 border border-border/40 rounded-xl p-4 text-text-muted text-xs italic"
                  >
                    <span className="font-bold text-text-muted/60">{dayName}</span>
                    <span>Rest Day / Ruhetag</span>
                  </div>
                );
              }

              const expanded = !!expandedWorkouts[workout.id];
              const phases = (workout.llm_plan as { phases?: WorkoutPhase[] })?.phases || [];
              const maxDuration = phases.length ? Math.max(...phases.map((p) => p.duration_min)) : 0;
              const isEditing = editingWorkout === workout.id;

              return (
                <Card key={workout.id} className="border-border/80">
                  <CardHeader className="cursor-pointer select-none" onClick={() => toggleWorkoutExpand(workout.id)}>
                    <div className="flex items-center justify-between w-full">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-accent uppercase tracking-wider">
                            {dayName}
                          </span>
                          <span className="h-1.5 w-1.5 rounded-full bg-border" />
                          <h3 className="font-bold text-sm text-text">{workout.name}</h3>
                        </div>
                        <div className="flex gap-3 text-xs text-text-muted tabular-nums">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            {Math.round((workout.duration_seconds ?? 0) / 60)} min
                          </span>
                          <span>
                            TSS: <strong className="text-text">{Math.round(workout.target_tss ?? 0)}</strong>
                          </span>
                          <span className="capitalize">{workout.workout_type}</span>
                          {workout.route_id && (
                            <span className="flex items-center gap-0.5 text-accent">
                              <MapPin className="h-3 w-3" /> Route
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            workout.status === "pushed"
                              ? "bg-accent/15 text-accent border border-accent/20"
                              : "bg-surface-2 text-text-muted border border-border"
                          }`}
                        >
                          {workout.status === "pushed" ? "Übertragen" : "Entwurf"}
                        </span>
                        {expanded ? <ChevronUp className="h-4.5 w-4.5" /> : <ChevronDown className="h-4.5 w-4.5" />}
                      </div>
                    </div>
                  </CardHeader>

                  {expanded && (
                    <CardBody className="border-t border-border/50 space-y-4 pt-4">
                      {isEditing ? (
                        <div className="space-y-4">
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
                              rows={8}
                              className="w-full px-3 py-2 text-sm font-mono bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
                            />
                          </div>

                          <div className="flex gap-2 justify-end pt-2">
                            <Button size="sm" variant="secondary" onClick={() => setEditingWorkout(null)}>
                              Abbrechen
                            </Button>
                            <Button size="sm" loading={savingWorkout} onClick={handleSaveWorkout}>
                              Speichern
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <>
                          {phases.length > 0 && (
                            <div className="space-y-1.5">
                              {phases.map((p, i) => (
                                <PhaseBar key={i} phase={p} maxDurationMin={maxDuration} />
                              ))}
                            </div>
                          )}

                          <CodeBlock code={workout.structured_text ?? ""} />

                          {workout.llm_reasoning && (
                            <div>
                              <h4 className="text-xs font-semibold text-text-secondary mb-1">
                                Begründung des Coaches
                              </h4>
                              <p className="text-xs leading-relaxed text-text-muted">{workout.llm_reasoning}</p>
                            </div>
                          )}

                          {workout.coach_notes && (
                            <div>
                              <h4 className="text-xs font-semibold text-text-secondary mb-1">Coach-Notizen</h4>
                              <p className="text-xs leading-relaxed text-text-muted">{workout.coach_notes}</p>
                            </div>
                          )}

                          <div className="flex gap-2 justify-end border-t border-border/50 pt-4">
                            <Button size="sm" variant="secondary" onClick={() => startEditWorkout(workout)}>
                              <Pencil className="h-3.5 w-3.5 mr-1.5" /> Bearbeiten
                            </Button>
                            {workout.status !== "pushed" && (
                              <Button size="sm" onClick={() => handlePushSingle(workout.id)}>
                                <Send className="h-3.5 w-3.5 mr-1.5" /> Zu Intervals.icu senden
                              </Button>
                            )}
                          </div>
                        </>
                      )}
                    </CardBody>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
