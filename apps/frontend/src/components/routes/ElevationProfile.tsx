"use client";

import { useMemo, useEffect } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
} from "recharts";
import type { TrackPoint, ClimbSegmentData } from "./RouteMap";

interface ElevationProfileProps {
  trackPoints: TrackPoint[];
  climbs: ClimbSegmentData[];
  activeClimbIndex?: number | null;
  onClimbClick?: (index: number) => void;
  onHoverPoint?: (point: TrackPoint | null) => void;
}

function getCategoryColor(category?: string | null): string {
  const cat = (category || "").toLowerCase();
  if (cat.includes("hc") || cat.includes("cat1")) return "#ef4444"; // Red
  if (cat.includes("cat2") || cat.includes("cat3")) return "#f97316"; // Orange
  if (cat.includes("cat4")) return "#10b981"; // Green
  return "#eab308"; // Amber / Yellow
}

function getCategoryLabel(category?: string | null): string {
  if (!category) return "ANSTIEG";
  return category.toUpperCase();
}

function findExactTrackPoint(allTrackPoints: TrackPoint[], targetKm: number): TrackPoint | null {
  if (!allTrackPoints || allTrackPoints.length === 0) return null;
  let low = 0;
  let high = allTrackPoints.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (allTrackPoints[mid].km < targetKm) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  if (low >= allTrackPoints.length) return allTrackPoints[allTrackPoints.length - 1];
  if (low === 0) return allTrackPoints[0];
  const prev = allTrackPoints[low - 1];
  const next = allTrackPoints[low];
  return Math.abs(prev.km - targetKm) < Math.abs(next.km - targetKm) ? prev : next;
}

function CustomTooltip({
  active,
  payload,
  climbs,
  allTrackPoints,
  onHoverPoint,
}: {
  active?: boolean;
  payload?: any[];
  climbs: ClimbSegmentData[];
  allTrackPoints: TrackPoint[];
  onHoverPoint?: (point: TrackPoint | null) => void;
}) {
  const sampledPt = active && payload && payload.length > 0 ? (payload[0].payload as TrackPoint) : null;
  const exactPt = useMemo(() => {
    if (!sampledPt) return null;
    return findExactTrackPoint(allTrackPoints, sampledPt.km) || sampledPt;
  }, [sampledPt, allTrackPoints]);

  useEffect(() => {
    if (onHoverPoint) {
      onHoverPoint(exactPt);
    }
  }, [exactPt, onHoverPoint]);

  if (!active || !exactPt) return null;

  const inClimbIndex = climbs.findIndex(
    (c) => exactPt.km >= c.start_km && exactPt.km <= c.end_km
  );
  const activeClimb = inClimbIndex >= 0 ? climbs[inClimbIndex] : null;

  return (
    <div className="bg-bg/95 backdrop-blur-md border border-border p-2.5 rounded-lg shadow-xl text-xs space-y-1 z-50 pointer-events-none">
      <div className="font-semibold text-text flex items-center justify-between gap-3">
        <span>km {exactPt.km.toFixed(1)}</span>
        <span className="text-accent font-bold">{Math.round(exactPt.ele)} m</span>
      </div>

      {activeClimb && (
        <div
          className="pt-1 mt-1 border-t border-border/60 text-[11px]"
          style={{ color: getCategoryColor(activeClimb.category) }}
        >
          <div className="font-bold flex items-center justify-between gap-2">
            <span>{getCategoryLabel(activeClimb.category)}</span>
            <span>Ø {activeClimb.avg_grade_pct}%</span>
          </div>
          <div className="text-text-muted text-[10px]">
            km {activeClimb.start_km} – {activeClimb.end_km} (+{Math.round(activeClimb.elevation_gain_m)} hm)
          </div>
        </div>
      )}
    </div>
  );
}

export default function ElevationProfile({
  trackPoints,
  climbs,
  activeClimbIndex,
  onClimbClick,
  onHoverPoint,
}: ElevationProfileProps) {
  // Downsample track points for chart rendering efficiency while preserving high resolution
  const chartData = useMemo(() => {
    if (!trackPoints || trackPoints.length === 0) return [];
    
    // Sample to max 1200 points for smooth performance and high resolution
    const maxPoints = 1200;
    const step = trackPoints.length > maxPoints ? Math.ceil(trackPoints.length / maxPoints) : 1;
    const sampled: Array<TrackPoint & { eleRounded: number; kmRounded: number }> = [];

    for (let i = 0; i < trackPoints.length; i += step) {
      const pt = trackPoints[i];
      sampled.push({
        ...pt,
        eleRounded: Math.round(pt.ele),
        kmRounded: Number(pt.km.toFixed(2)),
      });
    }

    // Always include the last point
    const lastPt = trackPoints[trackPoints.length - 1];
    if (sampled[sampled.length - 1] !== lastPt) {
      sampled.push({
        ...lastPt,
        eleRounded: Math.round(lastPt.ele),
        kmRounded: Number(lastPt.km.toFixed(2)),
      });
    }

    return sampled;
  }, [trackPoints]);

  const { minEle, maxEle } = useMemo(() => {
    if (!chartData.length) return { minEle: 0, maxEle: 500 };
    let min = chartData[0].ele;
    let max = chartData[0].ele;
    for (const pt of chartData) {
      if (pt.ele < min) min = pt.ele;
      if (pt.ele > max) max = pt.ele;
    }
    const padding = Math.max(20, (max - min) * 0.15);
    return {
      minEle: Math.max(0, Math.floor((min - padding) / 10) * 10),
      maxEle: Math.ceil((max + padding) / 10) * 10,
    };
  }, [chartData]);

  if (!chartData.length) return null;

  return (
    <div className="w-full bg-surface border border-border rounded-xl p-4 shadow-inner">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted">
          Höhenprofil ({chartData[chartData.length - 1].kmRounded} km)
        </h4>
        <div className="flex items-center gap-3 text-[11px] text-text-muted">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" /> HC / Cat 1
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" /> Cat 2 / 3
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Cat 4
          </span>
        </div>
      </div>

      <div className="w-full h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            onMouseMove={(state) => {
              if (state && state.activePayload && state.activePayload.length > 0) {
                const pt = state.activePayload[0].payload as TrackPoint;
                if (onHoverPoint) onHoverPoint(pt);
              }
            }}
            onMouseLeave={() => {
              if (onHoverPoint) onHoverPoint(null);
            }}
          >
            <defs>
              <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="kmRounded"
              type="number"
              domain={["dataMin", "dataMax"]}
              unit=" km"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
            />
            <YAxis
              domain={[minEle, maxEle]}
              unit=" m"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
            />

            <Tooltip
              content={<CustomTooltip climbs={climbs} allTrackPoints={trackPoints} onHoverPoint={onHoverPoint} />}
            />

            {/* Render climb segment reference areas */}
            {climbs.map((climb, idx) => {
              const color = getCategoryColor(climb.category);
              const isActive = activeClimbIndex === idx;

              return (
                <ReferenceArea
                  key={idx}
                  x1={climb.start_km}
                  x2={climb.end_km}
                  y1={minEle}
                  y2={maxEle}
                  fill={color}
                  fillOpacity={isActive ? 0.35 : 0.15}
                  stroke={color}
                  strokeOpacity={isActive ? 1.0 : 0.6}
                  strokeWidth={isActive ? 2 : 1}
                  strokeDasharray={isActive ? undefined : "3 3"}
                  style={{ pointerEvents: "none" }}
                  className="transition-all"
                />
              );
            })}

            <Area
              type="monotone"
              dataKey="ele"
              stroke="#06b6d4"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#elevationGradient)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
