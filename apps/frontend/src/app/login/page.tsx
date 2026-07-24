"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Lock } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export default function LoginPage() {
  const router = useRouter();
  const { user, status, login, bootstrap } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If already authenticated, bounce onward.
  useEffect(() => {
    if (status === "idle") void bootstrap();
  }, [status, bootstrap]);

  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(user.must_change_password ? "/change-password" : "/dashboard");
    }
  }, [status, user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const u = await login(email.trim().toLowerCase(), password);
      router.replace(u.must_change_password ? "/change-password" : "/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <img src="/brand/mark.svg" alt="TerraTrain" className="mx-auto mb-4 h-14 w-auto" />
          <h1 className="text-xl font-bold tracking-tight">Anmelden</h1>
          <p className="mt-1 text-sm text-text-muted">TerraTrain Entwickler-Login</p>
        </div>

        {/* Development Notice */}
        <div className="mb-4 rounded-lg border border-accent/30 bg-accent/10 p-3.5 text-xs text-text-secondary flex items-start gap-2.5">
          <Lock className="h-4 w-4 text-accent shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-accent block mb-0.5">App noch in Entwicklung</strong>
            Die öffentliche Registrierung ist derzeit geschlossen. Der Login ist aktuell nur für Entwickler und Tester freigeschaltet.
          </div>
        </div>

        <Card>
          <CardBody className="pt-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="E-Mail"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Input
                label="Passwort"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              {error && <p className="text-xs text-danger">{error}</p>}
              <Button type="submit" className="w-full" loading={submitting}>
                Anmelden
              </Button>
            </form>
          </CardBody>
        </Card>

        <div className="mt-6 text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Zurück zur Startseite
          </Link>
        </div>
      </div>
    </div>
  );
}
