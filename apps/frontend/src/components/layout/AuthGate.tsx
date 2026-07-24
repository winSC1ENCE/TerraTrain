"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { useAthleteStore } from "@/stores/athlete-store";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { useT } from "@/lib/i18n";

/**
 * Guards the authenticated app area. Resolution order:
 *   1. Resolve the session (/auth/me). Not logged in → /login.
 *   2. Force a password change on first login → /change-password.
 *   3. Load the user's athlete profile. None yet → /connect.
 *   4. Otherwise render the app.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const t = useT();
  const { user, status: authStatus, bootstrap: bootstrapAuth } = useAuthStore();
  const {
    athlete,
    status: athleteStatus,
    bootstrap: bootstrapAthlete,
  } = useAthleteStore();

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // 1. Resolve session.
  useEffect(() => {
    if (mounted && authStatus === "idle") void bootstrapAuth();
  }, [mounted, authStatus, bootstrapAuth]);

  // Not authenticated → login.
  useEffect(() => {
    if (authStatus === "anonymous") router.replace("/login");
  }, [authStatus, router]);

  // Forced password change on first login.
  useEffect(() => {
    if (authStatus === "authenticated" && user?.must_change_password) {
      router.replace("/change-password");
    }
  }, [authStatus, user, router]);

  // 2. Once authenticated (and password OK), resolve the athlete profile.
  useEffect(() => {
    if (
      authStatus === "authenticated" &&
      user &&
      !user.must_change_password &&
      athleteStatus === "idle"
    ) {
      void bootstrapAthlete();
    }
  }, [authStatus, user, athleteStatus, bootstrapAthlete]);

  // No athlete profile yet → onboarding.
  useEffect(() => {
    if (athleteStatus === "none") router.replace("/connect");
  }, [athleteStatus, router]);

  if (!mounted || authStatus === "idle" || authStatus === "loading") {
    return <FullPageSpinner />;
  }

  if (athleteStatus === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-sm text-text-secondary">{t.common.error}</p>
        <Button variant="secondary" size="sm" onClick={() => void bootstrapAthlete()}>
          {t.common.retry}
        </Button>
      </div>
    );
  }

  // Render only once the athlete profile is confirmed for THIS session — no
  // optimistic paint from persisted cache, since a stale athlete from a
  // previous user/session must not leak into the current one.
  if (
    authStatus === "authenticated" &&
    !user?.must_change_password &&
    athleteStatus === "ready" &&
    athlete
  ) {
    return <>{children}</>;
  }

  return <FullPageSpinner />;
}
