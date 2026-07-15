"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAthleteStore } from "@/stores/athlete-store";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { useT } from "@/lib/i18n";

export function AthleteGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const t = useT();
  const { athlete, status, bootstrap } = useAthleteStore();

  // After the first client-side effect, zustand's synchronous localStorage
  // rehydration is guaranteed complete — no onRehydrateStorage callback needed.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (mounted && status === "idle") {
      void bootstrap();
    }
  }, [mounted, status, bootstrap]);

  useEffect(() => {
    if (status === "none") {
      router.replace("/connect");
    }
  }, [status, router]);

  if (!mounted) return <FullPageSpinner />;

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
  if (athlete && (status === "ready" || status === "loading" || status === "idle")) {
    return <>{children}</>;
  }

  return <FullPageSpinner />;
}
