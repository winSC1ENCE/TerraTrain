import {
  Activity,
  Flame,
  Gauge,
  HeartPulse,
  Timer,
  TrendingUp,
  Zap,
} from "lucide-react";

export const WORKOUT_TYPES = [
  { value: "recovery", icon: HeartPulse },
  { value: "endurance", icon: Flame },
  { value: "tempo", icon: Gauge },
  { value: "threshold", icon: TrendingUp },
  { value: "vo2max", icon: Zap },
  { value: "anaerobic", icon: Activity },
  { value: "sprint", icon: Timer },
];

export function zoneColor(zone?: string | null): string {
  if (!zone) return "#94a3b8"; // default slate-400

  const z = zone.toLowerCase().trim();

  if (z.includes("z1") || z.includes("recovery") || z.includes("rekom")) {
    return "#38bdf8"; // sky-400
  }
  if (z.includes("z2") || z.includes("endurance") || z.includes("grundlage")) {
    return "#3b82f6"; // blue-500
  }
  if (z.includes("z3") || z.includes("tempo") || z.includes("sweetspot")) {
    return "#22c55e"; // green-500
  }
  if (z.includes("z4") || z.includes("threshold") || z.includes("schwelle")) {
    return "#eab308"; // yellow-500
  }
  if (z.includes("z5") || z.includes("vo2")) {
    return "#f97316"; // orange-500
  }
  if (z.includes("z6") || z.includes("anaerobic") || z.includes("anaerob")) {
    return "#ef4444"; // red-500
  }
  if (z.includes("z7") || z.includes("sprint")) {
    return "#a855f7"; // purple-500
  }

  return "#94a3b8";
}
