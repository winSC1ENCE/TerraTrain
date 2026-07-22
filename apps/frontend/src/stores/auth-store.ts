"use client";

import { create } from "zustand";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

type AuthStatus = "idle" | "loading" | "authenticated" | "anonymous";

interface AuthStore {
  user: User | null;
  status: AuthStatus;

  /** Resolve the current session from the httpOnly cookie via /auth/me. */
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  status: "idle",

  bootstrap: async () => {
    set({ status: "loading" });
    try {
      const user = await api.auth.me();
      set({ user, status: "authenticated" });
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        set({ user: null, status: "anonymous" });
      } else {
        // Network/other error — treat as anonymous so the app can route to login
        // rather than hanging on a spinner.
        set({ user: null, status: "anonymous" });
      }
    }
  },

  login: async (email, password) => {
    const user = await api.auth.login(email, password);
    set({ user, status: "authenticated" });
    return user;
  },

  logout: async () => {
    try {
      await api.auth.logout();
    } finally {
      set({ user: null, status: "anonymous" });
    }
  },

  setUser: (user) => set({ user, status: "authenticated" }),
}));

export const useUser = () => useAuthStore((s) => s.user);
