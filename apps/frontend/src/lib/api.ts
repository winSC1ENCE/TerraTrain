import type {
  Athlete,
  DocumentSearchResult,
  Route,
  SyncResult,
  User,
  WeeklyPlan,
  Workout,
} from "./types";

export type { Route };

const rawBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
export const API_BASE = rawBase.endsWith("/api/v1") ? rawBase : `${rawBase.replace(/\/$/, "")}/api/v1`;

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(?:^|; )terratrain_csrf=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : null;
}

export function csrfHeaders(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { "X-CSRF-Token": token } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  
  const headers: Record<string, string> = {
    ...csrfHeaders(),
    ...(options.headers as Record<string, string>),
  };

  // Only add Content-Type: application/json if not sending FormData
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let errorData: any = null;
    let errorMessage = `HTTP error ${response.status}`;
    try {
      errorData = await response.json();
      if (errorData?.detail) {
        errorMessage = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new ApiError(response.status, errorMessage, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  auth: {
    me: () => request<User>("/auth/me"),
    login: (email: string, password: string) =>
      request<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    logout: () =>
      request<void>("/auth/logout", {
        method: "POST",
      }),
    changePassword: (current_password: string, new_password: string) =>
      request<void>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password, new_password }),
      }),
  },

  athletes: {
    getMe: () => request<Athlete>("/athletes/me"),
    create: (data: Partial<Athlete> & { intervals_api_key?: string }) =>
      request<Athlete>("/athletes/me", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (data: Partial<Athlete> & { intervals_api_key?: string }) =>
      request<Athlete>("/athletes/me", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: () =>
      request<void>("/athletes/me", {
        method: "DELETE",
      }),
    sync: (days = 90) =>
      request<SyncResult>(`/athletes/me/sync?days=${days}`, {
        method: "POST",
      }),
  },

  fitness: {
    get: (days = 90) => request<any>(`/athletes/me/fitness?days=${days}`),
  },

  routes: {
    list: () => request<Route[]>("/routes"),
    get: (id: string) => request<Route>(`/routes/${id}`),
    upload: (formData: FormData) =>
      request<Route>("/routes/upload", {
        method: "POST",
        body: formData,
      }),
    update: (id: string, data: { name: string }) =>
      request<Route>(`/routes/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/routes/${id}`, {
        method: "DELETE",
      }),
  },

  workouts: {
    list: () => request<Workout[]>("/workouts"),
    get: (id: string) => request<Workout>(`/workouts/${id}`),
    push: (id: string) =>
      request<Workout>(`/workouts/${id}/push`, {
        method: "POST",
      }),
    update: (id: string, data: Partial<Workout>) =>
      request<Workout>(`/workouts/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/workouts/${id}`, {
        method: "DELETE",
      }),
  },

  weeklyPlans: {
    list: () => request<WeeklyPlan[]>("/weekly-plans"),
    get: (id: string) => request<WeeklyPlan>(`/weekly-plans/${id}`),
    delete: (id: string) =>
      request<void>(`/weekly-plans/${id}`, {
        method: "DELETE",
      }),
    push: (id: string) =>
      request<{ pushed_workout_ids: string[] }>(`/weekly-plans/${id}/push`, {
        method: "POST",
      }),
    detect: (startDate: string, mesocycleType: string) =>
      request<any>(
        `/weekly-plans/detect?start_date=${startDate}&mesocycle_type=${mesocycleType}`
      ),
  },

  documents: {
    list: () => request<any[]>("/documents"),
    ingest: (formData: FormData) =>
      request<{ chunks_created: number; filename: string }>("/documents/ingest", {
        method: "POST",
        body: formData,
      }),
    delete: (id: string) =>
      request<void>(`/documents/${id}`, {
        method: "DELETE",
      }),
    search: (query: string, k = 5) =>
      request<DocumentSearchResult[]>(
        `/documents/search?q=${encodeURIComponent(query)}&k=${k}`
      ),
  },
};
