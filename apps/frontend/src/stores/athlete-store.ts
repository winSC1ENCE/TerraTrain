"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";
import type { Athlete } from "@/lib/types";

export type Language = "de" | "en";
type AthleteStatus = "idle" | "loading" | "ready" | "none" | "error";

interface AthleteStore {
  athlete: Athlete | null; // persisted — instant paint on reload
  status: AthleteStatus; // NOT persisted
  lastSync: string | null; // persisted, ISO timestamp
  language: Language; // persisted, default "de"

  bootstrap: () => Promise<void>;
  setAthlete: (a: Athlete) => void;
  markSynced: () => void;
  setLanguage: (l: Language) => void;
  clear: () => void;
}

export const useAthleteStore = create<AthleteStore>()(
  persist(
    (set, get) => ({
      athlete: null,
      status: "idle",
      lastSync: null,
      language: "de",

      bootstrap: async () => {
        set({ status: "loading" });
        try {
          const list = await api.athletes.list();
          if (list.length === 0) {
            set({ athlete: null, status: "none" });
            return;
          }
          // single-user app: prefer previously-selected id, else first
          const prev = get().athlete?.id;
          const match = list.find((a) => a.id === prev) ?? list[0];
          set({ athlete: match, status: "ready" });
        } catch {
          set({ status: "error" });
        }
      },
      setAthlete: (a) => set({ athlete: a, status: "ready" }),
      markSynced: () => set({ lastSync: new Date().toISOString() }),
      setLanguage: (language) => set({ language }),
      clear: () => set({ athlete: null, status: "none", lastSync: null }),
    }),
    {
      name: "terratrain-athlete",
      partialize: (s) => ({
        athlete: s.athlete,
        lastSync: s.lastSync,
        language: s.language,
      }),
    }
  )
);

export const useAthlete = () => useAthleteStore((s) => s.athlete);
