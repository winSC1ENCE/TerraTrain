"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export interface TrackPoint {
  lat: number;
  lon: number;
  ele: number;
  km: number;
}

export interface ClimbSegmentData {
  start_km: number;
  end_km: number;
  avg_grade_pct: number;
  max_grade_pct: number;
  length_m: number;
  elevation_gain_m: number;
  vam?: number | null;
  category?: string | null;
}

interface RouteMapProps {
  trackPoints: TrackPoint[];
  climbs: ClimbSegmentData[];
  activeClimbIndex?: number | null;
  hoveredPoint?: TrackPoint | null;
  onClimbClick?: (index: number) => void;
}

function getCategoryColor(category?: string | null): string {
  const cat = (category || "").toLowerCase();
  if (cat.includes("hc") || cat.includes("cat1")) return "#ef4444"; // Crimson Red
  if (cat.includes("cat2") || cat.includes("cat3")) return "#f97316"; // Orange / Amber
  if (cat.includes("cat4")) return "#10b981"; // Emerald Green
  return "#eab308"; // Yellow default for climbs
}

export default function RouteMap({
  trackPoints,
  climbs,
  activeClimbIndex,
  hoveredPoint,
  onClimbClick,
}: RouteMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const climbPolylinesRef = useRef<L.Polyline[]>([]);
  const hoverMarkerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || !trackPoints || trackPoints.length === 0) return;

    // Initialize Leaflet map if not created yet
    if (!mapRef.current) {
      const map = L.map(mapContainerRef.current, {
        scrollWheelZoom: true,
        zoomControl: true,
      });

      // OpenTopoMap tile layer (Topographic hillshading and contours)
      const topoTiles = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
        maxZoom: 17,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
      });

      // Standard OpenStreetMap fallback / alternative layer
      const osmTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      });

      // Default to OpenTopoMap with OSM fallback control
      topoTiles.addTo(map);

      L.control
        .layers({
          Topografisch: topoTiles,
          Standard: osmTiles,
        })
        .addTo(map);

      mapRef.current = map;
    }

    const map = mapRef.current;

    // Clear previous route polylines and static markers (preserving hover marker)
    map.eachLayer((layer) => {
      if (layer instanceof L.Polyline || (layer instanceof L.Marker && layer !== hoverMarkerRef.current)) {
        map.removeLayer(layer);
      }
    });

    const latLons: L.LatLngTuple[] = trackPoints.map((pt) => [pt.lat, pt.lon]);

    // 1. Draw main route path (cyan / dark teal outline + bright cyan core)
    const mainPolyline = L.polyline(latLons, {
      color: "#06b6d4",
      weight: 5,
      opacity: 0.85,
    }).addTo(map);

    // Fit map bounds to main route
    map.fitBounds(mainPolyline.getBounds(), { padding: [30, 30] });

    // 2. Draw Start Marker (Green Flag) & Finish Marker (Checkered Flag)
    if (latLons.length > 0) {
      const startPoint = latLons[0];
      const endPoint = latLons[latLons.length - 1];

      const startIcon = L.divIcon({
        className: "custom-map-icon",
        html: `<div style="background-color: #10b981; color: white; width: 24px; height: 24px; borderRadius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">S</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const finishIcon = L.divIcon({
        className: "custom-map-icon",
        html: `<div style="background-color: #ef4444; color: white; width: 24px; height: 24px; borderRadius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">Z</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      L.marker(startPoint, { icon: startIcon }).bindTooltip("Start", { permanent: false }).addTo(map);
      L.marker(endPoint, { icon: finishIcon }).bindTooltip("Ziel", { permanent: false }).addTo(map);
    }

    // 3. Draw Peak Elevation Marker
    let maxElePt = trackPoints[0];
    for (const pt of trackPoints) {
      if (pt.ele > maxElePt.ele) maxElePt = pt;
    }
    if (maxElePt) {
      const peakIcon = L.divIcon({
        className: "custom-map-icon",
        html: `<div style="background-color: #8b5cf6; color: white; width: 26px; height: 26px; borderRadius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">▲</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });
      L.marker([maxElePt.lat, maxElePt.lon], { icon: peakIcon })
        .bindTooltip(`Höchster Punkt: ${Math.round(maxElePt.ele)}m`, { permanent: false })
        .addTo(map);
    }

    // 4. Draw Color-Coded Climb Segments
    climbPolylinesRef.current = [];

    climbs.forEach((climb, idx) => {
      const climbPoints = trackPoints.filter(
        (pt) => pt.km >= climb.start_km && pt.km <= climb.end_km
      );

      if (climbPoints.length < 2) return;

      const climbLatLons: L.LatLngTuple[] = climbPoints.map((pt) => [pt.lat, pt.lon]);
      const color = getCategoryColor(climb.category);
      const isActive = activeClimbIndex === idx;

      const climbPolyline = L.polyline(climbLatLons, {
        color: color,
        weight: isActive ? 9 : 7,
        opacity: isActive ? 1.0 : 0.9,
      }).addTo(map);

      // Tooltip content
      const catBadge = climb.category ? climb.category.toUpperCase() : "ANSTIEG";
      const tooltipHtml = `
        <div style="font-family: sans-serif; padding: 2px;">
          <div style="font-weight: bold; font-size: 12px; color: ${color};">
            ${catBadge} · km ${climb.start_km}–${climb.end_km}
          </div>
          <div style="font-size: 11px; color: #333; margin-top: 2px;">
            <b>Steigung:</b> Ø ${climb.avg_grade_pct}% (max ${climb.max_grade_pct}%)<br/>
            <b>Höhengewinn:</b> +${Math.round(climb.elevation_gain_m)} hm<br/>
            <b>Länge:</b> ${(climb.length_m / 1000).toFixed(1)} km
          </div>
        </div>
      `;

      climbPolyline.bindTooltip(tooltipHtml, { sticky: true });

      climbPolyline.on("click", () => {
        if (onClimbClick) onClimbClick(idx);
      });

      climbPolylinesRef.current[idx] = climbPolyline;
    });
  }, [trackPoints, climbs, activeClimbIndex, onClimbClick]);

  // Handle active climb highlighting zoom
  useEffect(() => {
    if (
      activeClimbIndex != null &&
      climbPolylinesRef.current[activeClimbIndex] &&
      mapRef.current
    ) {
      const poly = climbPolylinesRef.current[activeClimbIndex];
      mapRef.current.fitBounds(poly.getBounds(), { padding: [50, 50], maxZoom: 15 });
    }
  }, [activeClimbIndex]);

  // Handle elevation chart hover marker sync & auto-panning on map
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (!hoveredPoint) {
      if (hoverMarkerRef.current) {
        map.removeLayer(hoverMarkerRef.current);
        hoverMarkerRef.current = null;
      }
      return;
    }

    const pointLatLng: L.LatLngTuple = [hoveredPoint.lat, hoveredPoint.lon];
    const badgeText = `km ${hoveredPoint.km.toFixed(1)} · ${Math.round(hoveredPoint.ele)}m`;

    if (!hoverMarkerRef.current) {
      const hoverIcon = L.divIcon({
        className: "hover-marker-node",
        html: `
          <div style="position: relative; width: 0; height: 0; display: flex; align-items: center; justify-content: center; z-index: 9999;">
            <div style="position: absolute; width: 28px; height: 28px; border-radius: 50%; background-color: rgba(6, 182, 212, 0.4); transform: translate(-50%, -50%);"></div>
            <div style="position: absolute; width: 14px; height: 14px; border-radius: 50%; background-color: #06b6d4; border: 2.5px solid white; box-shadow: 0 0 12px rgba(6, 182, 212, 1), 0 2px 8px rgba(0,0,0,0.6); transform: translate(-50%, -50%);"></div>
            <div id="hover-marker-badge" style="position: absolute; left: 14px; top: -12px; white-space: nowrap; background: rgba(15, 23, 42, 0.95); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.5); padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; font-family: system-ui, -apple-system, sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.5); pointer-events: none;">
              ${badgeText}
            </div>
          </div>
        `,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });

      hoverMarkerRef.current = L.marker(pointLatLng, {
        icon: hoverIcon,
        zIndexOffset: 10000,
      }).addTo(map);
    } else {
      hoverMarkerRef.current.setLatLng(pointLatLng);
      const el = hoverMarkerRef.current.getElement();
      if (el) {
        const badgeEl = el.querySelector("#hover-marker-badge");
        if (badgeEl) badgeEl.textContent = badgeText;
      }
    }

    // Auto-pan map if marker moves outside current visible map bounds
    if (!map.getBounds().contains(pointLatLng)) {
      map.panTo(pointLatLng, { animate: false });
    }
  }, [hoveredPoint]);

  return (
    <div className="relative w-full h-[340px] rounded-xl overflow-hidden border border-border shadow-inner bg-surface">
      <div ref={mapContainerRef} className="w-full h-full z-0" />
    </div>
  );
}
