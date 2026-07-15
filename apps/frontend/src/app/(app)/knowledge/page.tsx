"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, FileText, Search, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { UploadZone } from "@/components/knowledge/UploadZone";
import type { DocumentSearchResult } from "@/lib/types";

export default function KnowledgePage() {
  const t = useT();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DocumentSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  const { data: documents } = useQuery({
    queryKey: ["documents"],
    queryFn: api.documents.list,
  });

  const deleteMutation = useMutation({
    mutationFn: api.documents.delete,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  async function handleUpload(file: File): Promise<string> {
    const form = new FormData();
    form.append("pdf_file", file);
    const res = await api.documents.ingest(form);
    void queryClient.invalidateQueries({ queryKey: ["documents"] });
    return `${res.chunks_created} ${t.knowledge.chunksCreated}`;
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      setResults(await api.documents.search(query.trim()));
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">{t.knowledge.title}</h1>
        <p className="mt-0.5 text-sm text-text-muted">{t.knowledge.subtitle}</p>
      </div>

      {/* Upload */}
      <UploadZone
        accept=".pdf,application/pdf"
        hint={t.knowledge.dropHint}
        busyHint={t.knowledge.uploadHint}
        onUpload={handleUpload}
      />

      {/* Document list */}
      <Card>
        <CardHeader>
          <CardTitle>{t.knowledge.documents}</CardTitle>
        </CardHeader>
        <CardBody>
          {!documents?.length ? (
            <EmptyState
              icon={BookOpen}
              title={t.knowledge.empty}
              description={t.knowledge.emptyHint}
            />
          ) : (
            <ul className="divide-y divide-border">
              {documents.map((doc) => (
                <li key={doc.document_id} className="flex items-center gap-3 py-2.5">
                  <FileText className="h-4 w-4 shrink-0 text-text-muted" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-text">{doc.title}</p>
                    <p className="truncate text-xs text-text-muted">{doc.source}</p>
                  </div>
                  <Badge>{doc.chunks} {t.knowledge.chunks}</Badge>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(doc.document_id)}
                    className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-danger/10 hover:text-danger"
                    aria-label={t.common.delete}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {/* Test search */}
      <Card>
        <CardHeader>
          <CardTitle>{t.knowledge.testSearch}</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1">
              <Input
                placeholder={t.knowledge.searchPlaceholder}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <Button type="submit" variant="secondary" loading={searching}>
              <Search className="h-3.5 w-3.5" />
              {t.common.search}
            </Button>
          </form>

          {results && (
            <ul className="space-y-2">
              {results.length === 0 && (
                <li className="text-xs text-text-muted">—</li>
              )}
              {results.map((r, i) => (
                <li key={i} className="rounded-lg bg-surface-2 p-3">
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-text-muted">{r.source}</span>
                    {r.score != null && (
                      <span className="flex shrink-0 items-center gap-1.5 text-xs text-text-muted">
                        {t.knowledge.relevance}
                        <span className="h-1 w-16 overflow-hidden rounded-full bg-border">
                          <span
                            className="block h-full bg-accent"
                            style={{ width: `${Math.round(r.score * 100)}%` }}
                          />
                        </span>
                      </span>
                    )}
                  </div>
                  <p className="line-clamp-3 text-xs leading-relaxed text-text-secondary">
                    {r.content}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <ConfirmDialog
        open={!!deleteTarget}
        title={t.common.delete}
        description={t.knowledge.deleteConfirm}
        confirmLabel={t.common.delete}
        cancelLabel={t.common.cancel}
        danger
        onConfirm={async () => {
          if (deleteTarget) await deleteMutation.mutateAsync(deleteTarget);
        }}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  );
}
