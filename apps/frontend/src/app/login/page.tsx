"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
      router.replace(user.must_change_password ? "/change-password" : "/");
    }
  }, [status, user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const u = await login(email.trim().toLowerCase(), password);
      router.replace(u.must_change_password ? "/change-password" : "/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <img src="/terratrain_logo.svg" alt="TerraTrain" className="mx-auto mb-4 h-16 w-auto" />
          <h1 className="text-xl font-bold tracking-tight">Anmelden</h1>
          <p className="mt-1 text-sm text-text-muted">Melde dich bei TerraTrain an</p>
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
      </div>
    </div>
  );
}
