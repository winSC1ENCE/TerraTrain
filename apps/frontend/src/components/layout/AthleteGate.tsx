"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAthleteStore } from "@/stores/athlete-store";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { useT } from "@/lib/i18n";

export function AthleteGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const t = useT();
  const { athlete, status, hydrated, bootstrap } = useAthleteStore();

  useEffect(() => {
    if (hydrated && status === "idle") {
      void bootstrap();
    }
  }, [hydrated, status, bootstrap]);

  useEffect(() => {
    if (status === "none") {
      router.replace("/connect");
    }
  }, [status, router]);

  if (!hydrated) return <FullPageSpinner />;

  if (status === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-sm text-text-secondary">{t.common.error}</p>
        <Button variant="secondary" size="sm" onClick={() => void bootstrap()}>
          {t.common.retry}
        </Button>
      </div>
    );
  }

  // Optimistic paint: cached athlete renders immediately while revalidating
  if (athlete && (status === "ready" || status === "loading")) {
    return <>{children}</>;
  }

  return <FullPageSpinner />;
}
