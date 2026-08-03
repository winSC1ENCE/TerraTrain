"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  Calendar,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Lock,
  MapPin,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Send,
  Sparkles,
  Trash,
} from "lucide-react";

import { api, API_BASE, csrfHeaders } from "@/lib/api";
import { useAthlete } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import type { Route, Sport, WeeklyPlan, Workout, WorkoutPhase } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { StreamPanel } from "@/components/coach/StreamPanel";
import { PhaseBar } from "@/components/coach/PhaseBar";

interface ScheduleItem {
  id: string;
  day_of_week: number;
  duration_min: number | "";
  sport?: Sport;
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

function getMonday(dateInput?: string | Date): string {
  const d = dateInput ? new Date(dateInput) : new Date();
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d.toISOString().split("T")[0];
}

function getISOWeekDetails(dateInput: string | Date) {
  const d = new Date(dateInput);
  const dayNum = d.getDay() || 7;
  d.setDate(d.getDate() + 4 - dayNum);
  const yearStart = new Date(d.getFullYear(), 0, 1);
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { weekNumber: weekNo, year: d.getFullYear() };
}

function formatWeekRange(mondayStr: string) {
  const mon = new Date(mondayStr);
  const sun = new Date(mon);
  sun.setDate(mon.getDate() + 6);
  const iso = getISOWeekDetails(mon);

  const pad = (n: number) => n.toString().padStart(2, "0");
  const monFmt = `${pad(mon.getDate())}.${pad(mon.getMonth() + 1)}.`;
  const sunFmt = `${pad(sun.getDate())}.${pad(sun.getMonth() + 1)}.${sun.getFullYear()}`;

  return {
    weekNumber: iso.weekNumber,
    year: iso.year,
    label: `KW ${iso.weekNumber} (${monFmt} - ${sunFmt})`,
    shortLabel: `KW ${iso.weekNumber}`,
    startDate: mondayStr,
    endDate: sun.toISOString().split("T")[0],
  };
}

function getWeekOptions() {
  const currentMon = getMonday();
  const options = [];

  for (let offset = -4; offset <= 8; offset++) {
    const d = new Date(currentMon);
    d.setDate(d.getDate() + offset * 7);
    const dateStr = d.toISOString().split("T")[0];
    const range = formatWeekRange(dateStr);

    let tag = "";
    if (offset === 0) tag = " (Diese Woche)";
    else if (offset === 1) tag = " (Nächste Woche)";
    else if (offset === -1) tag = " (Letzte Woche)";

    options.push({
      value: dateStr,
      label: `${range.label}${tag}`,
      weekNumber: range.weekNumber,
      isCurrent: offset === 0,
    });
  }
  return options;
}

import { Slider } from "@/components/ui/Slider";

const DEFAULT_SCHEDULES: ScheduleItem[] = [
  { id: "1", day_of_week: 1, duration_min: 90, route_id: "", notes: "" },
  { id: "3", day_of_week: 3, duration_min: 90, route_id: "", notes: "" },
  { id: "5", day_of_week: 5, duration_min: 120, route_id: "", notes: "" },
  { id: "6", day_of_week: 6, duration_min: 90, route_id: "", notes: "" },
];

export default function WeeklyPlannerPage() {
  const athlete = useAthlete();
  const t = useT();

  const [showForm, setShowForm] = useState(false);

  // Restore draft state from sessionStorage if present
  const [startDate, setStartDate] = useState(() => {
    if (typeof window === "undefined") return getMonday();
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.startDate) return parsed.startDate;
      }
    } catch {}
    return getMonday();
  });

  const [mesocycleType, setMesocycleType] = useState(() => {
    if (typeof window === "undefined") return "3-1";
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.mesocycleType) return parsed.mesocycleType;
      }
    } catch {}
    return "3-1";
  });

  const [weekType, setWeekType] = useState(() => {
    if (typeof window === "undefined") return "load_1";
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.weekType) return parsed.weekType;
      }
    } catch {}
    return "load_1";
  });

  const [aggressiveness, setAggressiveness] = useState<number>(() => {
    if (typeof window === "undefined") return 0;
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.aggressiveness === "number") return parsed.aggressiveness;
      }
    } catch {}
    return 0;
  });

  const [globalNotes, setGlobalNotes] = useState(() => {
    if (typeof window === "undefined") return "";
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.globalNotes !== undefined) return parsed.globalNotes;
      }
    } catch {}
    return "";
  });

  const [provider, setProvider] = useState(() => {
    if (typeof window === "undefined") return "ollama";
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.provider) return parsed.provider;
      }
    } catch {}
    return "ollama";
  });

  const [pressLap, setPressLap] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.pressLap === "boolean") return parsed.pressLap;
      }
    } catch {}
    return false;
  });

  // Day schedules setup
  const [schedules, setSchedules] = useState<ScheduleItem[]>(() => {
    if (typeof window === "undefined") return DEFAULT_SCHEDULES;
    try {
      const saved = sessionStorage.getItem("terratrain_planner_draft_v1");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed.schedules) && parsed.schedules.length > 0) {
          return parsed.schedules;
        }
      }
    } catch {}
    return DEFAULT_SCHEDULES;
  });

  // Persisted plan details
  const [generatedPlan, setGeneratedPlan] = useState<WeeklyPlan | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const saved = sessionStorage.getItem("terratrain_active_plan_v1");
      if (saved) {
        return JSON.parse(saved);
      }
    } catch {}
    return null;
  });

  // Auto-save draft changes to sessionStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const draft = {
        startDate,
        mesocycleType,
        weekType,
        aggressiveness,
        globalNotes,
        provider,
        pressLap,
        schedules,
      };
      sessionStorage.setItem("terratrain_planner_draft_v1", JSON.stringify(draft));
    } catch (e) {
      console.error("Failed to cache planner draft", e);
    }
  }, [startDate, mesocycleType, weekType, aggressiveness, globalNotes, provider, pressLap, schedules]);

  // Auto-save active plan to sessionStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (generatedPlan) {
        sessionStorage.setItem("terratrain_active_plan_v1", JSON.stringify(generatedPlan));
      } else {
        sessionStorage.removeItem("terratrain_active_plan_v1");
      }
    } catch (e) {
      console.error("Failed to cache active plan", e);
    }
  }, [generatedPlan]);

  const resetDraftForm = () => {
    setStartDate(getMonday());
    setMesocycleType("3-1");
    setWeekType("load_1");
    setAggressiveness(0);
    setGlobalNotes("");
    setProvider("ollama");
    setPressLap(false);
    setSchedules(DEFAULT_SCHEDULES);
    setGeneratedPlan(null);
    setShowForm(true);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("terratrain_planner_draft_v1");
      sessionStorage.removeItem("terratrain_active_plan_v1");
    }
  };

  // Detection states
  const [detection, setDetection] = useState<{
    selected_week?: {
      week_number: number;
      year: number;
      start_date: string;
      end_date: string;
      formatted: string;
    };
    history: Array<{
      week_label: string;
      week_number?: number;
      week_offset?: string;
      start_date: string;
      end_date: string;
      date_range_formatted?: string;
      tss: number;
    }>;
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
  const [generatedPlan, setGeneratedPlan] = useState<WeeklyPlan | null>(null);

  // Tab & search states
  const [activeTab, setActiveTab] = useState<"new" | "history">("new");
  const [searchQuery, setSearchQuery] = useState("");

  // Expanded workouts
  const [expandedWorkouts, setExpandedWorkouts] = useState<Record<string, boolean>>({});
  // Editing state for workouts
  const [editingWorkout, setEditingWorkout] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editStructuredText, setEditStructuredText] = useState("");
  const [editSport, setEditSport] = useState<Sport>("cycling");
  const [editPressLap, setEditPressLap] = useState(false);
  const [savingWorkout, setSavingWorkout] = useState(false);
  const [pushingAll, setPushingAll] = useState(false);

  // Fetch routes
  const { data: routes } = useQuery({
    queryKey: ["routes", athlete?.id],
    queryFn: () => api.routes.list(),
    enabled: !!athlete,
  });

  // Fetch weekly plans
  const { data: weeklyPlans, refetch: refetchPlans } = useQuery({
    queryKey: ["weeklyPlans", athlete?.id],
    queryFn: () => api.weeklyPlans.list(),
    enabled: !!athlete,
  });

  // Query mesocycle detection
  useEffect(() => {
    if (!athlete || !startDate) return;
    setDetectLoading(true);
    api.weeklyPlans
      .detect(startDate, mesocycleType)
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
      start_date: startDate,
      mesocycle_type: mesocycleType,
      week_type: weekType,
      aggressiveness: aggressiveness,
      schedules: activeDays.map((s) => ({
        day_of_week: s.day_of_week,
        duration_min: typeof s.duration_min === "number" && !isNaN(s.duration_min) ? s.duration_min : (parseFloat(s.duration_min as string) || 90),
        sport: s.sport || athlete?.sport || "cycling",
        route_id: s.route_id || null,
        notes: s.notes || null,
      })),
      notes: globalNotes || null,
      provider: provider,
      press_lap: pressLap,
    };

    try {
      let res = await fetch(`${API_BASE}/weekly-plans/generate`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (res.status === 401) {
        const refreshed = await api.auth.refresh().then(() => true).catch(() => false);
        if (refreshed) {
          res = await fetch(`${API_BASE}/weekly-plans/generate`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json", ...csrfHeaders() },
            body: JSON.stringify(body),
            signal: controller.signal,
          });
        }
      }

      if (!res.ok) {
        if (res.status === 401) {
          setStreamError("Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.");
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
          setIsStreaming(false);
          return;
        }
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
            setShowForm(false);
            refetchPlans();
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
      refetchPlans();
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
      refetchPlans();
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
        refetchPlans();
      }
    } catch (err) {
      alert((err as Error).message);
    }
  }

  function startEditWorkout(w: Workout) {
    setEditingWorkout(w.id);
    setEditName(w.name);
    setEditStructuredText(w.structured_text ?? "");
    setEditSport(w.sport);
    setEditPressLap(w.press_lap ?? false);
  }

  async function handleSaveWorkout() {
    if (!editingWorkout || !generatedPlan) return;
    setSavingWorkout(true);
    try {
      await api.workouts.update(editingWorkout, {
        name: editName,
        structured_text: editStructuredText,
        sport: editSport,
        press_lap: editPressLap,
      });
      const fullPlan = await api.weeklyPlans.get(generatedPlan.id);
      setGeneratedPlan(fullPlan);
      refetchPlans();
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

  function isPastWeek(startDateStr: string) {
    if (!startDateStr) return false;
    const now = new Date();
    const day = now.getDay();
    const diff = day === 0 ? -6 : 1 - day; // Monday of current week
    const currentMonday = new Date(now);
    currentMonday.setDate(now.getDate() + diff);
    currentMonday.setHours(0, 0, 0, 0);
    const planDate = new Date(startDateStr);
    planDate.setHours(0, 0, 0, 0);

    return planDate.getTime() < currentMonday.getTime();
  }

  // Filtered plans list
  const filteredPlans = weeklyPlans?.filter((plan) => {
    const query = searchQuery.toLowerCase();
    if (!query) return true;
    
    const formattedDate = new Date(plan.start_date).toLocaleDateString("de-CH");
    return (
      plan.start_date.toLowerCase().includes(query) ||
      formattedDate.toLowerCase().includes(query) ||
      plan.mesocycle_type.toLowerCase().includes(query) ||
      (plan.week_type && plan.week_type.toLowerCase().includes(query)) ||
      (plan.coach_rationale && plan.coach_rationale.toLowerCase().includes(query)) ||
      (plan.notes && plan.notes.toLowerCase().includes(query))
    );
  }) ?? [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <Calendar className="h-5 w-5 text-accent" />
            {t.nav.weeklyPlanner}
          </h1>
          <p className="mt-0.5 text-sm text-text-muted">
            Plane deine gesamte Woche mit Mesozyklus-Periodisierung.
          </p>
        </div>
        <div className="flex bg-surface border border-border rounded-lg p-0.5 self-start md:self-auto">
          <button
            onClick={() => setActiveTab("new")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === "new"
                ? "bg-bg text-text shadow-sm"
                : "text-text-muted hover:text-text"
            }`}
          >
            {generatedPlan ? "Aktueller Plan" : "Neuer Plan"}
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === "history"
                ? "bg-bg text-text shadow-sm"
                : "text-text-muted hover:text-text"
            }`}
          >
            Vorhandene Pläne
          </button>
        </div>
      </div>

      {activeTab === "history" ? (
        <div className="space-y-6">
          <div className="flex gap-4 items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
              <input
                type="text"
                placeholder="Pläne durchsuchen (z. B. 20.07.2026, 3:1, Belastung)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm bg-surface border border-border rounded-lg text-text focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>

          {filteredPlans.length === 0 ? (
            <div className="text-center py-12 text-text-muted border border-dashed border-border/80 rounded-xl bg-surface/50">
              <CalendarDays className="h-8 w-8 mx-auto text-text-muted/60 mb-2" />
              <p className="text-sm">Keine Wochenpläne gefunden.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredPlans.map((plan) => {
                const totalWorkouts = plan.workouts?.length ?? 0;
                const formattedDate = new Date(plan.start_date).toLocaleDateString("de-CH", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                });
                const isPast = isPastWeek(plan.start_date);

                return (
                  <Card key={plan.id} className="border-border/80 hover:border-accent/40 transition-colors">
                    <CardHeader className="flex flex-row items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-accent uppercase tracking-wider">
                            Woche ab {formattedDate}
                          </span>
                          {isPast ? (
                            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-surface-2 text-text-muted border border-border">
                              <Lock className="h-2.5 w-2.5" /> Archiv
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-accent/15 text-accent border border-accent/20">
                              Aktiv
                            </span>
                          )}
                        </div>
                        <h3 className="font-bold text-sm text-text">
                          {plan.mesocycle_type} Zyklus • {(plan.week_type || "").startsWith("load") ? `Belastungswoche ${(plan.week_type || "").split("_")[1] || "1"}` : "Erholungswoche"}
                        </h3>
                        <p className="text-xs text-text-muted mt-1">
                          {totalWorkouts} Einheiten geplant
                        </p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => {
                          setGeneratedPlan(plan);
                          setShowForm(false);
                          setActiveTab("new");
                        }}
                      >
                        {isPast ? "Ansehen" : "Auswählen & Bearbeiten"}
                      </Button>
                    </CardHeader>
                    {plan.notes && (
                      <CardBody className="pt-0 pb-3 border-t border-border/20 mt-2">
                        <p className="text-xs italic text-text-muted line-clamp-2 mt-2">
                          Notiz: {plan.notes}
                        </p>
                      </CardBody>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {generatedPlan && (
            <div className="bg-surface border border-border/80 rounded-xl p-3 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs">
              <div className="text-xs">
                <span className="font-semibold text-text">Erstellter Wochenplan:</span>{" "}
                <span className="text-accent font-bold">
                  Woche ab {new Date(generatedPlan.start_date).toLocaleDateString("de-CH")} ({generatedPlan.mesocycle_type} Zyklus)
                </span>
              </div>
              <div className="flex gap-2">
                {showForm ? (
                  <Button size="xs" variant="primary" onClick={() => setShowForm(false)}>
                    <FileText className="h-3.5 w-3.5 mr-1" /> Plan anzeigen
                  </Button>
                ) : (
                  <Button size="xs" variant="outline" onClick={() => setShowForm(true)}>
                    <Pencil className="h-3.5 w-3.5 mr-1" /> Formular / Bearbeiten
                  </Button>
                )}
                <Button size="xs" variant="secondary" onClick={resetDraftForm}>
                  <RotateCcw className="h-3.5 w-3.5 mr-1" /> Neuen Plan beginnen
                </Button>
              </div>
            </div>
          )}

          {(!generatedPlan || showForm) && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              {/* Settings Panel */}
              <div className="lg:col-span-4 space-y-6">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Sparkles className="h-4.5 w-4.5 text-accent" /> Periodisierung & Wochenwahl
                    </CardTitle>
                    <Button
                      type="button"
                      variant="secondary"
                      size="xs"
                      onClick={resetDraftForm}
                      title="Entwurf zurücksetzen"
                    >
                      <RotateCcw className="h-3 w-3 mr-1" /> Zurücksetzen
                    </Button>
                  </CardHeader>
                  <CardBody className="space-y-4 pt-1">
                    {/* Quick Week Selectors */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-text-muted">Schnellauswahl</label>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          size="xs"
                          variant={startDate === getMonday() ? "primary" : "outline"}
                          onClick={() => setStartDate(getMonday())}
                        >
                          Diese Woche ({formatWeekRange(getMonday()).shortLabel})
                        </Button>
                        <Button
                          type="button"
                          size="xs"
                          variant={
                            startDate === getMonday(new Date(Date.now() + 7 * 86400000))
                              ? "primary"
                              : "outline"
                          }
                          onClick={() =>
                            setStartDate(getMonday(new Date(Date.now() + 7 * 86400000)))
                          }
                        >
                          Nächste Woche (
                          {formatWeekRange(getMonday(new Date(Date.now() + 7 * 86400000))).shortLabel}
                          )
                        </Button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Select
                        label="Trainingswoche wählen"
                        value={startDate}
                        onChange={(e) => setStartDate(getMonday(e.target.value))}
                      >
                        {getWeekOptions().map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </Select>

                      <Select
                        label="Periodisierung"
                        value={mesocycleType}
                        onChange={(e) => setMesocycleType(e.target.value)}
                      >
                        <option value="3-1">3:1 Zyklus</option>
                        <option value="2-1">2:1 Zyklus</option>
                      </Select>
                    </div>

                    <div className="text-xs">
                      <Input
                        label="Startdatum (Mo der gewählten Woche)"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(getMonday(e.target.value))}
                      />
                    </div>

                    {/* Auto detection section */}
                    <div className="bg-surface-2 rounded-lg p-3 border border-border/50 text-xs space-y-2">
                      <div className="font-semibold text-text flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <Activity className="h-3.5 w-3.5 text-accent" /> Meso-Erkennung (Past Load)
                        </span>
                        {detectLoading && <span className="animate-pulse text-accent">Lädt...</span>}
                      </div>

                      <div className="text-[11px] text-text-muted bg-surface/60 rounded p-2 border border-border/30">
                        🎯 <span className="font-medium text-text">Gewählte Trainingswoche:</span>{" "}
                        <span className="font-semibold text-accent">
                          {detection?.selected_week?.formatted || formatWeekRange(startDate).label}
                        </span>
                      </div>

                      {detection && !detectLoading ? (
                        <>
                          <div className="text-[11px] text-text-muted mt-2 font-medium">
                            Vergangene 4 Wochen Trainingsbelastung:
                          </div>
                          <div className="grid grid-cols-4 gap-1.5 pt-1">
                            {detection.history.map((h, i) => (
                              <div
                                key={i}
                                className="bg-surface border border-border/70 rounded p-1.5 text-center shadow-xs"
                              >
                                <div className="text-[10px] font-bold text-accent">
                                  {h.week_label}
                                </div>
                                <div className="text-[9px] text-text-muted leading-tight">
                                  {h.date_range_formatted || h.week_offset}
                                </div>
                                <div className="font-extrabold text-text text-sm mt-1">
                                  {Math.round(h.tss)}
                                </div>
                                <div className="text-[8px] text-text-muted uppercase tracking-wider">
                                  TSS
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="text-[11px] text-accent mt-2 font-medium bg-accent/5 p-2 rounded border border-accent/20">
                            Empfehlung: {detection.reasoning}
                          </div>
                        </>
                      ) : (
                        <div className="text-text-muted py-1">
                          Wähle eine Trainingswoche, um die 4 vergangenen Wochen zu analysieren.
                        </div>
                      )}
                    </div>

                    <Select
                      label="Wochen-Typ"
                      value={weekType}
                      onChange={(e) => setWeekType(e.target.value)}
                    >
                      <option value="load_1">Belastungswoche 1</option>
                      <option value="load_2">Belastungswoche 2</option>
                      <option value="load_3">Belastungswoche 3</option>
                      <option value="recovery">Erholungswoche</option>
                    </Select>

                    <Slider
                      label="Trainingsbelastung / Aggressivität"
                      hint="Steuert die Ziel-Intensität/TSS (0 = Ausgewogen / Normal wie bisher, +1/+2 = Intensiver / Mehr Belastung, -1/-2 = Leichter / Konservativ)"
                      value={aggressiveness}
                      onChange={setAggressiveness}
                    />

                    <Select
                      label="Modell-Anbieter"
                      value={provider}
                      onChange={(e) => setProvider(e.target.value)}
                    >
                      <option value="gemini">Gemini (Cloud)</option>
                      <option value="ollama">Ollama (Lokal)</option>
                    </Select>

                    <Textarea
                      label="Globale Coach-Hinweise (optional)"
                      value={globalNotes}
                      onChange={(e) => setGlobalNotes(e.target.value)}
                      placeholder="Z. B. 'Fokus auf Klettern' oder 'Bin leicht erkältet'..."
                      rows={3}
                    />

                    <Checkbox
                      label={t.workouts.pressLap}
                      hint={t.workouts.pressLapHint}
                      checked={pressLap}
                      onChange={setPressLap}
                    />

                    <Button
                      className="w-full"
                      onClick={handleGenerate}
                      disabled={isStreaming}
                      loading={isStreaming}
                    >
                      Wochenplan erstellen
                    </Button>
                  </CardBody>
                </Card>

                {isStreaming && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm font-semibold flex items-center justify-between">
                        <span>Der Coach denkt nach…</span>
                        <Button variant="secondary" size="sm" onClick={handleStop}>
                          Stoppen
                        </Button>
                      </CardTitle>
                    </CardHeader>
                    <CardBody className="pt-0">
                      {streamError ? (
                        <div className="bg-danger/10 border border-danger/20 text-danger text-xs rounded-lg p-3 flex gap-2 items-start mt-2">
                          <AlertCircle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold">Fehler beim Generieren:</span>
                            <p className="mt-0.5">{streamError}</p>
                          </div>
                        </div>
                      ) : (
                        <StreamPanel events={events} isStreaming={isStreaming} />
                      )}
                    </CardBody>
                  </Card>
                )}
              </div>

              {/* Day Schedules Creator */}
              <div className="lg:col-span-8 space-y-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Activity className="h-4.5 w-4.5 text-accent" /> Wochenplaner-Kalender ({activeDays.length} Trainingseinheiten)
                    </CardTitle>
                  </CardHeader>
                  <CardBody className="space-y-4 pt-1">
                    {DAYS_OF_WEEK.map((dayName, idx) => {
                      const daySchedules = activeDays.filter((s) => s.day_of_week === idx);
                      return (
                        <div key={idx} className="border-b border-border/40 pb-3 last:border-b-0 last:pb-0">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-bold text-text">{dayName}</span>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                setSchedules((prev) => [
                                  ...prev,
                                  {
                                    id: Math.random().toString(),
                                    day_of_week: idx,
                                    duration_min: 90,
                                    sport: athlete?.sport ?? "cycling",
                                    route_id: "",
                                    notes: "",
                                  },
                                ]);
                              }}
                            >
                              <Plus className="h-3 w-3 mr-1" /> Einheit hinzufügen
                            </Button>
                          </div>

                          {daySchedules.length > 0 ? (
                            <div className="space-y-2 pl-3">
                              {daySchedules.map((sched, sIdx) => (
                                <div key={sched.id} className="flex gap-3 items-end bg-surface-2 p-2 rounded-lg border border-border/30">
                                  <div className="flex flex-col gap-0.5 min-w-[75px]">
                                    <span className="text-[10px] font-bold text-accent uppercase">Einheit {sIdx + 1}</span>
                                    <Input
                                      type="number"
                                      value={sched.duration_min}
                                      onChange={(e) => {
                                        const raw = e.target.value;
                                        const val = raw === "" ? "" : (isNaN(parseFloat(raw)) ? "" : parseFloat(raw));
                                        setSchedules((prev) =>
                                          prev.map((s) => (s.id === sched.id ? { ...s, duration_min: val } : s))
                                        );
                                      }}
                                      className="py-1 text-xs"
                                      placeholder="Minuten"
                                    />
                                    {typeof sched.duration_min === "number" && sched.duration_min > 0 && sched.duration_min < 10 && (
                                      <span className="text-[9px] text-warning font-medium leading-none mt-0.5">Unter 10 Min.</span>
                                    )}
                                  </div>
                                  <div className="w-36">
                                    <Select
                                      value={sched.sport || athlete?.sport || "cycling"}
                                      onChange={(e) => {
                                        const val = e.target.value as Sport;
                                        setSchedules((prev) =>
                                          prev.map((s) => (s.id === sched.id ? { ...s, sport: val } : s))
                                        );
                                      }}
                                      className="py-1 text-xs"
                                    >
                                      <option value="cycling">{t.settings.sports.cycling}</option>
                                      <option value="running">{t.settings.sports.running}</option>
                                      <option value="swimming">{t.settings.sports.swimming}</option>
                                      <option value="cross_country_skiing">{t.settings.sports.cross_country_skiing}</option>
                                      <option value="weight_training">{t.settings.sports.weight_training}</option>
                                    </Select>
                                  </div>
                                  <div className="flex-1">
                                    <Select
                                      value={sched.route_id || ""}
                                      onChange={(e) => {
                                        const val = e.target.value;
                                        setSchedules((prev) =>
                                          prev.map((s) => (s.id === sched.id ? { ...s, route_id: val } : s))
                                        );
                                      }}
                                      className="py-1 text-xs"
                                    >
                                      <option value="">Keine Route</option>
                                      {routes?.map((r) => (
                                        <option key={r.id} value={r.id}>
                                          {r.name} ({Math.round(r.distance_m / 1000)} km)
                                        </option>
                                      ))}
                                    </Select>
                                  </div>
                                  <div className="flex-1">
                                    <Input
                                      type="text"
                                      value={sched.notes || ""}
                                      onChange={(e) => {
                                        const val = e.target.value;
                                        setSchedules((prev) =>
                                          prev.map((s) => (s.id === sched.id ? { ...s, notes: val } : s))
                                        );
                                      }}
                                      className="py-1 text-xs"
                                      placeholder="Z. B. 'Nur lockeres Flachland'..."
                                    />
                                  </div>
                                  <Button
                                    variant="danger"
                                    size="sm"
                                    onClick={() => {
                                      setSchedules((prev) => prev.filter((s) => s.id !== sched.id));
                                    }}
                                  >
                                    <Trash className="h-3 w-3" />
                                  </Button>
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
          {generatedPlan && !showForm && (
            <div className="space-y-6">
              {(() => {
                const isPast = isPastWeek(generatedPlan.start_date);
                return (
                  <>
                    <Card className="border-accent/40 bg-accent/5">
                      <CardHeader className="flex flex-row items-start justify-between">
                        <div>
                          <CardTitle sub="Erstellter Trainingsplan">
                            <span className="flex items-center gap-2">
                              Woche ab Montag, {new Date(generatedPlan.start_date).toLocaleDateString("de-CH")}
                              {isPast && (
                                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-medium bg-surface border border-border text-text-muted">
                                  <Lock className="h-2.5 w-2.5" /> Archiviert (Schreibgeschützt)
                                </span>
                              )}
                            </span>
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
                                  : `Belastung (Woche ${(generatedPlan.week_type || "").split("_")[1] || "1"})`}
                              </strong>
                            </span>
                            <span>
                              Einheiten: <strong className="text-text">{generatedPlan.workouts.length}</strong>
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="secondary" size="sm" onClick={() => setGeneratedPlan(null)}>
                            Neuen Plan erstellen
                          </Button>
                          {!isPast && (
                            <>
                              <Button variant="danger" size="sm" onClick={handleDeletePlan}>
                                Plan löschen
                              </Button>
                              <Button size="sm" onClick={handlePushAll} loading={pushingAll}>
                                Ganze Woche übertragen
                              </Button>
                            </>
                          )}
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
                        // Find all workouts for this day_of_week
                        const dayWorkouts = generatedPlan.workouts.filter((w) => {
                          const wDate = new Date(w.scheduled_date!);
                          const startDt = new Date(generatedPlan.start_date);
                          const diffDays = Math.round((wDate.getTime() - startDt.getTime()) / (1000 * 3600 * 24));
                          return diffDays === idx;
                        });

                        if (dayWorkouts.length === 0) {
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

                        return (
                          <div key={idx} className="space-y-3">
                            {dayWorkouts.map((workout, wIdx) => {
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
                                            {dayName} {dayWorkouts.length > 1 ? `#${wIdx + 1}` : ""}
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
                                              rows={8}
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
                                            {!isPast && (
                                              <>
                                                <Button size="sm" variant="secondary" onClick={() => startEditWorkout(workout)}>
                                                  <Pencil className="h-3.5 w-3.5 mr-1.5" /> Bearbeiten
                                                </Button>
                                                {workout.status !== "pushed" && (
                                                  <Button size="sm" onClick={() => handlePushSingle(workout.id)}>
                                                    <Send className="h-3.5 w-3.5 mr-1.5" /> Zu Intervals.icu senden
                                                  </Button>
                                                )}
                                              </>
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
                        );
                      })}
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </>
      )}
    </div>
  );
}
