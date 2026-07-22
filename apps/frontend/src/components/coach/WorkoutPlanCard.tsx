"use client";

import { useState } from "react";
import { CheckCircle2, Send, Pencil } from "lucide-react";
import { api } from "@/lib/api";
import type { CoachPlan, WorkoutPhase } from "@/lib/types";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { PhaseBar } from "./PhaseBar";

export function WorkoutPlanCard({
  plan,
  phases,
}: {
  plan: CoachPlan;
  phases?: WorkoutPhase[];
}) {
  const t = useT();
  const [pushing, setPushing] = useState(false);
  const [pushed, setPushed] = useState(plan.status === "pushed");
  const [pushError, setPushError] = useState<string | null>(null);

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(plan.name);
  const [editStructuredText, setEditStructuredText] = useState(plan.structured_text);
  const [displayName, setDisplayName] = useState(plan.name);
  const [displayStructuredText, setDisplayStructuredText] = useState(plan.structured_text);
  const [saving, setSaving] = useState(false);

  const maxDuration = phases?.length
    ? Math.max(...phases.map((p) => p.duration_min))
    : 0;
  const totalMin = phases?.reduce((acc, p) => acc + p.duration_min * Math.max(1, p.repeat), 0);

  async function handlePush() {
    setPushing(true);
    setPushError(null);
    try {
      await api.workouts.push(plan.workout_id);
      setPushed(true);
    } catch (err) {
      setPushError((err as Error).message);
    } finally {
      setPushing(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.workouts.update(plan.workout_id, {
        name: editName,
        structured_text: editStructuredText,
      });
      setDisplayName(editName);
      setDisplayStructuredText(editStructuredText);
      setIsEditing(false);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (isEditing) {
    return (
      <Card className="border-accent/30">
        <CardHeader>
          <CardTitle sub="Workout bearbeiten">Details anpassen</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">Workout-Name</label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">Intervals.icu Schritte</label>
            <textarea
              value={editStructuredText}
              onChange={(e) => setEditStructuredText(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 text-sm font-mono bg-bg border border-border rounded-md text-text focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setIsEditing(false)}
            >
              Abbrechen
            </Button>
            <Button
              size="sm"
              loading={saving}
              onClick={handleSave}
            >
              Speichern
            </Button>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className="border-accent/30">
      <CardHeader>
        <CardTitle sub={t.coach.planReady}>{displayName}</CardTitle>
        <div className="flex gap-3 text-xs text-text-muted tabular-nums">
          <span>
            {t.coach.targetTss}: <strong className="text-text">{Math.round(plan.target_tss)}</strong>
          </span>
          {totalMin ? (
            <span>
              {t.coach.duration}: <strong className="text-text">{Math.round(totalMin)} min</strong>
            </span>
          ) : null}
        </div>
      </CardHeader>
      <CardBody className="space-y-4">
        {phases && phases.length > 0 && (
          <div className="space-y-1.5">
            {phases.map((p, i) => (
              <PhaseBar key={i} phase={p} maxDurationMin={maxDuration} />
            ))}
          </div>
        )}

        <CodeBlock code={displayStructuredText} />

        {plan.rationale && (
          <div>
            <h3 className="mb-1 text-xs font-semibold text-text-secondary">
              {t.coach.reasoning}
            </h3>
            <p className="text-xs leading-relaxed text-text-muted">{plan.rationale}</p>
          </div>
        )}

        <div className="flex items-center gap-3">
          {pushed ? (
            <span className="flex items-center gap-1.5 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" /> {t.coach.pushed}
            </span>
          ) : (
            <>
              <Button onClick={handlePush} loading={pushing} size="sm">
                <Send className="h-3.5 w-3.5" />
                {t.coach.pushToIntervals}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setEditName(displayName);
                  setEditStructuredText(displayStructuredText);
                  setIsEditing(true);
                }}
              >
                <Pencil className="h-3.5 w-3.5" />
                Bearbeiten
              </Button>
            </>
          )}
          {pushError && <span className="text-xs text-danger">{pushError}</span>}
        </div>
      </CardBody>
    </Card>
  );
}
