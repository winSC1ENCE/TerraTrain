"use client";

import { useRef, useState } from "react";
import { CheckCircle2, FileUp, XCircle } from "lucide-react";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/utils";

export interface UploadItem {
  name: string;
  status: "queued" | "uploading" | "done" | "error";
  detail?: string;
}

export function UploadZone({
  accept,
  hint,
  busyHint,
  onUpload,
}: {
  accept: string;
  hint: string;
  busyHint?: string;
  onUpload: (file: File) => Promise<string>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const processingRef = useRef(false);

  async function enqueue(files: FileList | File[]) {
    const items = Array.from(files);
    setQueue((q) => [...q, ...items.map((f) => ({ name: f.name, status: "queued" as const }))]);

    if (processingRef.current) return;
    processingRef.current = true;

    // Sequential uploads — the backend ingests synchronously
    for (const file of items) {
      setQueue((q) =>
        q.map((it) =>
          it.name === file.name && it.status === "queued"
            ? { ...it, status: "uploading" }
            : it
        )
      );
      try {
        const detail = await onUpload(file);
        setQueue((q) =>
          q.map((it) =>
            it.name === file.name && it.status === "uploading"
              ? { ...it, status: "done", detail }
              : it
          )
        );
      } catch (err) {
        setQueue((q) =>
          q.map((it) =>
            it.name === file.name && it.status === "uploading"
              ? { ...it, status: "error", detail: (err as Error).message }
              : it
          )
        );
      }
    }
    processingRef.current = false;
  }

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files.length) void enqueue(e.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging
            ? "border-accent bg-accent/5"
            : "border-border hover:border-border-strong"
        )}
      >
        <FileUp className="h-6 w-6 text-text-muted" />
        <p className="text-sm text-text-secondary">{hint}</p>
        {busyHint && <p className="text-xs text-text-muted">{busyHint}</p>}
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) void enqueue(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {queue.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {queue.map((item, i) => (
            <li
              key={`${item.name}-${i}`}
              className="flex items-center gap-2 rounded-lg bg-surface-2 px-3 py-2 text-xs"
            >
              {item.status === "uploading" && <Spinner size={14} />}
              {item.status === "queued" && (
                <span className="h-3.5 w-3.5 rounded-full border border-border-strong" />
              )}
              {item.status === "done" && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
              {item.status === "error" && <XCircle className="h-3.5 w-3.5 text-danger" />}
              <span className="truncate text-text-secondary">{item.name}</span>
              {item.detail && (
                <span
                  className={cn(
                    "ml-auto shrink-0",
                    item.status === "error" ? "text-danger" : "text-text-muted"
                  )}
                >
                  {item.detail}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
