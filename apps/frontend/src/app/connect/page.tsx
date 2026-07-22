"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bike, CheckCircle2, Footprints, Medal } from "lucide-react";
import { api } from "@/lib/api";
import { useAthleteStore } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { Athlete, SyncResult } from "@/lib/types";

type Step = "form" | "syncing" | "success";

export default function ConnectPage() {
  const router = useRouter();
  const t = useT();
  const { status, setAthlete, markSynced } = useAthleteStore();

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [step, setStep] = useState<Step>("form");
  const [intervalsId, setIntervalsId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [name, setName] = useState("");
  const [sport, setSport] = useState("cycling");
  const [error, setError] = useState<string | null>(null);
  const [athlete, setLocalAthlete] = useState<Athlete | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);

  // Already connected? Go to dashboard.
  useEffect(() => {
    if (mounted && status === "ready") router.replace("/");
  }, [mounted, status, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStep("syncing");

    let created: Athlete;
    try {
      created = await api.athletes.create({
        intervals_user_id: intervalsId.trim(),
        name: name.trim(),
        sport,
        intervals_api_key: apiKey.trim(),
      });
    } catch (err) {
      setError((err as Error).message);
      setStep("form");
      return;
    }

    try {
      const sync = await api.athletes.sync(created.id);
      const fresh = await api.athletes.get(created.id);
      setLocalAthlete(fresh);
      setSyncResult(sync);
      setAthlete(fresh);
      markSynced();
    } catch {
      setLocalAthlete(created);
      setSyncFailed(true);
      setAthlete(created);
    }
    setStep("success");
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <img src="/terratrain_logo.svg" alt="TerraTrain Logo" className="mx-auto mb-4 h-16 w-auto" />
          <h1 className="text-xl font-bold tracking-tight">{t.connect.title}</h1>
          <p className="mt-1 text-sm text-text-muted">{t.connect.subtitle}</p>
        </div>

        <Card>
          <CardBody className="pt-5">
            {step === "form" && (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label={t.connect.name}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
                <div>
                  <span className="block text-xs font-medium text-text-secondary mb-1.5">
                    {t.connect.sport}
                  </span>
                  <SegmentedControl
                    options={[
                      { value: "cycling", label: t.settings.sports.cycling, icon: Bike },
                      { value: "running", label: t.settings.sports.running, icon: Footprints },
                      { value: "triathlon", label: t.settings.sports.triathlon, icon: Medal },
                    ]}
                    value={sport}
                    onChange={setSport}
                  />
                </div>
                <Input
                  label={t.connect.athleteId}
                  hint={t.connect.athleteIdHint}
                  placeholder="i123456"
                  value={intervalsId}
                  onChange={(e) => setIntervalsId(e.target.value)}
                  required
                />
                <Input
                  label={t.connect.apiKey}
                  hint={t.connect.apiKeyHint}
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  required
                />
                {error && <p className="text-xs text-danger">{error}</p>}
                <Button type="submit" className="w-full">
                  {t.connect.submit}
                </Button>
              </form>
            )}

            {step === "syncing" && (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <Button loading variant="ghost" disabled>
                  {t.connect.connecting}
                </Button>
                <p className="text-xs text-text-muted">{t.connect.syncing}</p>
              </div>
            )}

            {step === "success" && athlete && (
              <div className="py-2 text-center">
                <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-success" />
                <h2 className="text-base font-semibold">{t.connect.successTitle}</h2>
                <p className="mt-1 text-sm text-text-secondary">{athlete.name}</p>

                <div className="mt-4 grid grid-cols-3 gap-2">
                  <SuccessStat label="FTP" value={athlete.ftp_watts ? `${athlete.ftp_watts} W` : "—"} />
                  <SuccessStat
                    label={t.settings.weight}
                    value={athlete.weight_kg ? `${athlete.weight_kg} kg` : "—"}
                  />
                  <SuccessStat
                    label={t.connect.sessions}
                    value={syncResult ? String(syncResult.sessions_synced) : "—"}
                  />
                </div>

                {syncFailed && (
                  <p className="mt-3 text-xs text-warning">{t.connect.syncFailed}</p>
                )}

                <Button className="mt-5 w-full" onClick={() => router.replace("/")}>
                  {t.connect.goToDashboard}
                </Button>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function SuccessStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-2 border border-border px-2 py-3">
      <p className="text-[10px] uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-0.5 text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}
