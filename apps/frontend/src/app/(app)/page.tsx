"use client";

import { Scale, TrendingUp, Zap } from "lucide-react";
import { useAthlete } from "@/stores/athlete-store";
import { useFitness } from "@/hooks/useFitness";
import { useT } from "@/lib/i18n";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { FormGauge } from "@/components/dashboard/FormGauge";
import { PmcChart } from "@/components/dashboard/PmcChart";
import { RecentWorkouts } from "@/components/dashboard/RecentWorkouts";

export default function DashboardPage() {
  const athlete = useAthlete();
  const t = useT();
  const { data: fitness, isLoading } = useFitness(athlete?.id);

  if (!athlete) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold tracking-tight">{t.dashboard.title}</h1>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          label={t.dashboard.ftp}
          value={athlete.ftp_watts ?? "—"}
          unit="W"
          icon={Zap}
        />
        <StatCard
          label={t.dashboard.weight}
          value={athlete.weight_kg ?? "—"}
          unit="kg"
          icon={Scale}
        />
        <StatCard
          label={t.dashboard.fitness}
          value={fitness?.current.ctl ?? "—"}
          accent="#3987e5"
          sub={
            fitness ? (
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                {t.dashboard.rampRate}: {fitness.current.ramp_rate_7d > 0 ? "+" : ""}
                {fitness.current.ramp_rate_7d}
              </span>
            ) : undefined
          }
        />
        <StatCard
          label={t.dashboard.fatigue}
          value={fitness?.current.atl ?? "—"}
          accent="#d55181"
        />
        <div className="col-span-2 lg:col-span-1">
          {fitness ? (
            <FormGauge tsb={fitness.current.tsb} />
          ) : (
            <Skeleton className="h-full min-h-[120px]" />
          )}
        </div>
      </div>

      {/* PMC chart */}
      <Card>
        <CardHeader>
          <CardTitle sub={t.dashboard.pmcSubtitle}>{t.dashboard.pmcTitle}</CardTitle>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : fitness?.series.length ? (
            <PmcChart series={fitness.series} />
          ) : (
            <p className="py-10 text-center text-sm text-text-muted">—</p>
          )}
        </CardBody>
      </Card>

      <RecentWorkouts athleteId={athlete.id} />
    </div>
  );
}
