"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useAthleteStore } from "@/stores/athlete-store";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/utils";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function Topbar() {
  const t = useT();
  const { athlete, lastSync, markSynced, setAthlete } = useAthleteStore();
  const [syncing, setSyncing] = useState(false);

  async function handleSync() {
    if (!athlete || syncing) return;
    setSyncing(true);
    try {
      await api.athletes.sync(athlete.id);
      const fresh = await api.athletes.get(athlete.id);
      setAthlete(fresh);
      markSynced();
    } finally {
      setSyncing(false);
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-bg/80 backdrop-blur px-4 lg:px-8">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-text">{athlete?.name}</span>
        {athlete?.ftp_watts && (
          <span className="rounded-md bg-surface-2 border border-border px-2 py-0.5 text-xs text-text-secondary tabular-nums">
            FTP {athlete.ftp_watts} W
          </span>
        )}
      </div>
      <button
        type="button"
        onClick={handleSync}
        disabled={syncing}
        className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-text-muted hover:text-text-secondary hover:bg-surface-2 transition-colors"
        title={t.topbar.syncNow}
      >
        <RefreshCw className={cn("h-3.5 w-3.5", syncing && "animate-spin")} />
        <span className="hidden sm:block">
          {syncing
            ? t.topbar.syncing
            : `${t.topbar.lastSync}: ${relativeTime(lastSync ?? "", t.topbar.never)}`}
        </span>
      </button>
    </header>
  );
}
