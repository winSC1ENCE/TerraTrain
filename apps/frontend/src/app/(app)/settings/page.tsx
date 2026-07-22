"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAthleteStore } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

export default function SettingsPage() {
  const router = useRouter();
  const t = useT();
  const { athlete, language, setLanguage, setAthlete, markSynced, clear } =
    useAthleteStore();

  const [name, setName] = useState(athlete?.name ?? "");
  const [sport, setSport] = useState<string>(athlete?.sport ?? "cycling");
  const [ftp, setFtp] = useState(athlete?.ftp_watts?.toString() ?? "");
  const [weight, setWeight] = useState(athlete?.weight_kg?.toString() ?? "");
  const [lthr, setLthr] = useState(athlete?.lthr?.toString() ?? "");
  const [maxHr, setMaxHr] = useState(athlete?.max_hr?.toString() ?? "");
  const [restingHr, setRestingHr] = useState(athlete?.resting_hr?.toString() ?? "");
  const [newApiKey, setNewApiKey] = useState("");

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!athlete) return null;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!athlete) return;
    setSaving(true);
    setSaved(false);
    try {
      const body: Record<string, unknown> = {
        name: name.trim() || undefined,
        sport: sport || undefined,
        ftp_watts: ftp ? Number(ftp) : undefined,
        weight_kg: weight ? Number(weight) : undefined,
        lthr: lthr ? Number(lthr) : undefined,
        max_hr: maxHr ? Number(maxHr) : undefined,
        resting_hr: restingHr ? Number(restingHr) : undefined,
      };
      if (newApiKey.trim()) body.intervals_api_key = newApiKey.trim();
      const updated = await api.athletes.update(athlete.id, body);
      setAthlete(updated);
      setNewApiKey("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }

  async function handleResync() {
    if (!athlete) return;
    setSyncing(true);
    setSyncMsg(null);
    try {
      const result = await api.athletes.sync(athlete.id);
      const fresh = await api.athletes.get(athlete.id);
      setAthlete(fresh);
      markSynced();
      setSyncMsg(t.settings.syncSuccess.replace("{n}", String(result.sessions_synced)));
    } catch (err) {
      setSyncMsg((err as Error).message);
    } finally {
      setSyncing(false);
    }
  }

  async function handleDisconnect() {
    if (!athlete) return;
    await api.athletes.delete(athlete.id);
    clear();
    router.replace("/connect");
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold tracking-tight">{t.settings.title}</h1>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle>{t.settings.profile}</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input label={t.settings.name} value={name} onChange={(e) => setName(e.target.value)} />
              <Select
                label={t.settings.sport}
                value={sport}
                onChange={(e) => setSport(e.target.value)}
              >
                <option value="cycling">{t.settings.sports.cycling}</option>
                <option value="running">{t.settings.sports.running}</option>
                <option value="swimming">{t.settings.sports.swimming}</option>
                <option value="cross_country_skiing">{t.settings.sports.cross_country_skiing}</option>
                <option value="weight_training">{t.settings.sports.weight_training}</option>
              </Select>
              <Input
                label={t.settings.ftp}
                type="number"
                value={ftp}
                onChange={(e) => setFtp(e.target.value)}
              />
              <Input
                label={t.settings.weight}
                type="number"
                step="0.1"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
              />
              <Input
                label={t.settings.lthr}
                type="number"
                value={lthr}
                onChange={(e) => setLthr(e.target.value)}
              />
              <Input
                label={t.settings.maxHr}
                type="number"
                value={maxHr}
                onChange={(e) => setMaxHr(e.target.value)}
              />
              <Input
                label={t.settings.restingHr}
                type="number"
                value={restingHr}
                onChange={(e) => setRestingHr(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" loading={saving}>
                {t.common.save}
              </Button>
              {saved && <span className="text-xs text-success">{t.settings.saved}</span>}
            </div>
          </form>
        </CardBody>
      </Card>

      {/* Intervals.icu */}
      <Card>
        <CardHeader>
          <CardTitle>{t.settings.intervals}</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <Input label={t.settings.athleteId} value={athlete.intervals_user_id} readOnly disabled />
          <Input
            label={t.settings.apiKey}
            hint={t.settings.apiKeyHint}
            type="password"
            placeholder="••••••••"
            value={newApiKey}
            onChange={(e) => setNewApiKey(e.target.value)}
          />
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={handleResync} loading={syncing}>
              {t.settings.resync}
            </Button>
            {syncMsg && <span className="text-xs text-text-secondary">{syncMsg}</span>}
          </div>
        </CardBody>
      </Card>

      {/* Language */}
      <Card>
        <CardHeader>
          <CardTitle>{t.settings.language}</CardTitle>
        </CardHeader>
        <CardBody>
          <SegmentedControl
            options={[
              { value: "de" as const, label: "Deutsch" },
              { value: "en" as const, label: "English" },
            ]}
            value={language}
            onChange={setLanguage}
          />
        </CardBody>
      </Card>

      {/* Danger zone */}
      <Card className="border-danger/30">
        <CardHeader>
          <CardTitle className="text-danger">{t.settings.dangerZone}</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="mb-3 text-xs text-text-muted">{t.settings.disconnectHint}</p>
          <Button variant="danger" size="sm" onClick={() => setConfirmOpen(true)}>
            {t.settings.disconnect}
          </Button>
        </CardBody>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        title={t.settings.disconnect}
        description={t.settings.disconnectConfirm}
        confirmLabel={t.common.delete}
        cancelLabel={t.common.cancel}
        danger
        onConfirm={handleDisconnect}
        onClose={() => setConfirmOpen(false)}
      />
    </div>
  );
}
