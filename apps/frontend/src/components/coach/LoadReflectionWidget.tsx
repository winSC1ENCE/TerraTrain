"use client";

import { Activity, Zap, TrendingUp, AlertCircle, ShieldCheck } from "lucide-react";
import type { WeeklyPlan, Workout } from "@/lib/types";

interface LoadReflectionWidgetProps {
  scheduledDate?: string;
  selectedWeeklyPlan?: WeeklyPlan | null;
  selectedWorkout?: Workout | null;
  loadPolicy: "target" | "allow_exceed" | "allow_fall_below";
  aggressiveness: number;
}

export function LoadReflectionWidget({
  scheduledDate,
  selectedWeeklyPlan,
  selectedWorkout,
  loadPolicy,
  aggressiveness,
}: LoadReflectionWidgetProps) {
  // Day Load Calculation
  const existingDayTss = selectedWorkout?.target_tss ?? 65;
  const estimatedDayTss = Math.round(existingDayTss * (1 + aggressiveness * 0.15));

  // Weekly Load Calculation
  const weekTotalTss = selectedWeeklyPlan?.workouts
    ? selectedWeeklyPlan.workouts.reduce((acc: number, w: Workout) => acc + (w.target_tss || 0), 0)
    : 350;

  const targetWeekTss = selectedWeeklyPlan?.target_tss ?? 400;

  const getPolicyBadge = () => {
    switch (loadPolicy) {
      case "allow_exceed":
        return {
          label: "Überlastung erlaubt (Overreach)",
          color: "border-warning/40 bg-warning/10 text-warning",
          icon: TrendingUp,
          desc: "TSS darf Tages- & Wochentargets überschreiten für Reizmaximierung",
        };
      case "allow_fall_below":
        return {
          label: "Unterbelastung erlaubt (Regeneration)",
          color: "border-info/40 bg-info/10 text-info",
          icon: ShieldCheck,
          desc: "TSS darf unter Tages- & Wochentargets fallen für Erholung",
        };
      default:
        return {
          label: "Ausgewogen (Zielbelastung)",
          color: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
          icon: Zap,
          desc: "Einhaltung der regulären PMC & Wochenplan Zielwerte",
        };
    }
  };

  const badge = getPolicyBadge();
  const BadgeIcon = badge.icon;

  return (
    <div className="rounded-xl border border-border-muted bg-background-card/80 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-text-primary">
            Trainingsbelastung / Load-Analyse
          </span>
        </div>
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${badge.color}`}>
          <BadgeIcon className="h-3 w-3" />
          {badge.label}
        </div>
      </div>

      <p className="text-[11px] text-text-muted">{badge.desc}</p>

      <div className="grid grid-cols-2 gap-3 pt-1">
        {/* Day Load */}
        <div className="rounded-lg border border-border-muted/60 bg-background-subtle p-3">
          <span className="text-[11px] font-medium text-text-muted block">Tagesbelastung (Day Load)</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-text-primary">~{estimatedDayTss}</span>
            <span className="text-xs text-text-muted">TSS</span>
          </div>
          <p className="text-[10px] text-text-secondary mt-1">
            {scheduledDate ? `Datum: ${scheduledDate}` : "Standard-Tagesziel"}
          </p>
        </div>

        {/* Week Load */}
        <div className="rounded-lg border border-border-muted/60 bg-background-subtle p-3">
          <span className="text-[11px] font-medium text-text-muted block">Wochenbelastung (Week Load)</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-primary">{weekTotalTss}</span>
            <span className="text-xs text-text-muted">/ {targetWeekTss} TSS</span>
          </div>
          <p className="text-[10px] text-text-secondary mt-1">
            {selectedWeeklyPlan ? `KW ${selectedWeeklyPlan.start_date}` : "Kumulierte Wochenplanung"}
          </p>
        </div>
      </div>
    </div>
  );
}
