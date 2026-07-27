import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr?: string | Date | null): string {
  if (!dateStr) return "";
  const d = typeof dateStr === "string" ? new Date(dateStr) : dateStr;
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null || isNaN(seconds) || seconds <= 0) return "0m";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);

  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
  return `${minutes}m`;
}

export function formatDistance(meters?: number | null): string {
  if (meters == null || isNaN(meters)) return "0 m";
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)} km`;
  }
  return `${Math.round(meters)} m`;
}

export function relativeTime(
  dateStr?: string | Date | null,
  fallback = "nie"
): string {
  if (!dateStr) return fallback;
  const d = typeof dateStr === "string" ? new Date(dateStr) : dateStr;
  if (isNaN(d.getTime())) return fallback;

  const now = new Date();
  const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);

  if (diffSec < 60) return "gerade eben";
  if (diffSec < 3600) return `vor ${Math.floor(diffSec / 60)} Min.`;
  if (diffSec < 86400) return `vor ${Math.floor(diffSec / 3600)} Std.`;
  if (diffSec < 604800) return `vor ${Math.floor(diffSec / 86400)} Tagen`;

  return formatDate(d);
}

export function tsbLabelKey(tsb: number): "fresh" | "optimal" | "neutral" | "tired" | "danger" {
  if (tsb > 25) return "fresh";
  if (tsb >= 5) return "optimal";
  if (tsb >= -10) return "neutral";
  if (tsb >= -30) return "tired";
  return "danger";
}
