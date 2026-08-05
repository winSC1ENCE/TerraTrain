"use client";

import { useState } from "react";
import { Upload, FileUp, CheckCircle, AlertCircle, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import type { Route, Sport } from "@/lib/types";

interface GpxDropzoneProps {
  sport?: Sport;
  onRouteUploaded: (route: Route) => void;
  selectedRoute?: Route | null;
}

export function GpxDropzone({ sport = "cycling", onRouteUploaded, selectedRoute }: GpxDropzoneProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  async function handleFileSelect(file: File) {
    if (!file.name.toLowerCase().endsWith(".gpx")) {
      setError("Bitte wähle eine gültige .gpx Datei aus.");
      return;
    }

    setUploading(true);
    setError(null);

    const routeName = file.name.replace(/\.gpx$/i, "");
    try {
      const formData = new FormData();
      formData.append("name", routeName);
      formData.append("sport", sport);
      formData.append("gpx_file", file);
      const route = await api.routes.upload(formData);
      onRouteUploaded(route);
    } catch (err) {
      setError((err as Error).message || "Fehler beim Hochladen der GPX-Datei.");
    } finally {
      setUploading(false);
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="space-y-1.5">
      <span className="block text-xs font-medium text-text-secondary">
        GPX Route direkt hochladen
      </span>

      {selectedRoute ? (
        <div className="flex items-center justify-between rounded-lg border border-primary/40 bg-primary/10 p-3 text-xs">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary shrink-0" />
            <div>
              <p className="font-semibold text-text-primary">{selectedRoute.name}</p>
              <p className="text-text-muted">
                {(selectedRoute.distance_m / 1000).toFixed(1)} km | {Math.round(selectedRoute.elevation_gain_m)} hm Höhengewinn
              </p>
            </div>
          </div>
          <span className="flex items-center gap-1 text-emerald-400 font-medium text-[11px]">
            <CheckCircle className="h-3.5 w-3.5" /> Ausgewählt
          </span>
        </div>
      ) : (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-3 text-center transition-colors ${
            dragActive
              ? "border-primary bg-primary/10"
              : "border-border-muted hover:border-primary/50 bg-background-card"
          }`}
        >
          <input
            type="file"
            accept=".gpx"
            disabled={uploading}
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileSelect(e.target.files[0]);
            }}
            className="absolute inset-0 z-10 opacity-0 cursor-pointer disabled:cursor-not-allowed"
          />
          <FileUp className="h-5 w-5 text-text-muted mb-1" />
          <p className="text-xs font-medium text-text-primary">
            {uploading ? "GPX wird analysiert..." : "GPX-Datei hier ablegen oder klicken"}
          </p>
          <p className="text-[11px] text-text-muted mt-0.5">
            Automatische Strecken- & Höhenprofilanalyse für Intervallanpassung
          </p>
        </div>
      )}

      {error && (
        <p className="text-xs text-danger flex items-center gap-1 mt-1">
          <AlertCircle className="h-3.5 w-3.5" /> {error}
        </p>
      )}
    </div>
  );
}
