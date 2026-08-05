export type Sport =
  | "cycling"
  | "running"
  | "swimming"
  | "cross_country_skiing"
  | "weight_training"
  | "other";

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_admin?: boolean;
  role?: string;
  must_change_password?: boolean;
  created_at?: string;
}

export interface Athlete {
  id: string;
  user_id: string;
  name: string;
  sport: Sport;
  intervals_user_id?: string | null;
  ftp_watts?: number | null;
  threshold_pace_s_per_m?: number | null;
  lthr?: number | null;
  max_hr?: number | null;
  resting_hr?: number | null;
  weight_kg?: number | null;
  vo2max?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface SyncResult {
  sessions_synced: number;
  profile_updated?: boolean;
  message?: string;
  synced_wellness?: number;
  synced_workouts?: number;
}

export interface WorkoutPhase {
  name: string;
  duration_min: number;
  zone: string;
  target_power_pct?: number | null;
  repeat: number;
  duration_s?: number;
  target_watts?: number;
  target_hr?: number;
  target_cadence?: number;
}

export interface CoachPlan {
  workout_id: string;
  name: string;
  title?: string;
  description?: string;
  structured_text: string;
  phases?: WorkoutPhase[];
  target_tss: number;
  rationale?: string;
  status?: string;
}

export interface CoachingRequest {
  workout_type: string;
  sport: Sport;
  aggressiveness?: number;
  scheduled_date?: string;
  notes?: string;
  route_id?: string;
  auto_push?: boolean;
  provider?: string;
  press_lap?: boolean;
  load_policy?: "target" | "allow_exceed" | "allow_fall_below";
  weekly_plan_id?: string;
  source_workout_id?: string;
}

export interface Workout {
  id: string;
  athlete_id: string;
  name: string;
  sport: Sport;
  workout_type?: string;
  structured_text?: string | null;
  description?: string | null;
  scheduled_date?: string | null;
  duration_seconds?: number | null;
  target_tss?: number | null;
  status?: string;
  intervals_workout_id?: string | null;
  press_lap?: boolean;
  route_id?: string | null;
  weekly_plan_id?: string | null;
  llm_plan?: Record<string, any> | null;
  llm_reasoning?: string | null;
  coach_notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ClimbSegment {
  start_km: number;
  end_km: number;
  avg_grade_pct: number;
  max_grade_pct: number;
  length_m: number;
  elevation_gain_m: number;
  vam?: number | null;
  category?: string | null;
}

export interface TrackPoint {
  lat: number;
  lon: number;
  ele: number;
  km: number;
  dist_m?: number;
}

export interface Route {
  id: string;
  athlete_id: string;
  name: string;
  sport: Sport;
  gpx_data?: string;
  surface_type?: string | null;
  distance_m: number;
  elevation_gain_m: number;
  elevation_loss_m?: number;
  max_elevation_m?: number | null;
  min_elevation_m?: number | null;
  climb_profile: ClimbSegment[];
  terrain_score?: number | null;
  created_at?: string;
  analysis?: {
    track_points?: TrackPoint[];
    climbs?: ClimbSegment[];
    [key: string]: any;
  } | null;
}

export interface WeeklyPlan {
  id: string;
  athlete_id: string;
  start_date: string;
  mesocycle_type: string;
  week_type?: string;
  coach_rationale?: string | null;
  target_tss?: number;
  workouts: Workout[];
  created_at?: string;
  updated_at?: string;
  notes?: string | null;
}

export interface DocumentSearchResult {
  content: string;
  source: string;
  score?: number;
  document_id?: string;
  title?: string;
}

export interface FitnessPoint {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
  tss?: number;
  ramp_rate_7d?: number;
}
