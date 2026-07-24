"use client";

import { useEffect } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bike,
  BookOpen,
  Brain,
  Calendar,
  Dumbbell,
  Footprints,
  Gauge,
  LineChart,
  Link2,
  Map as MapIcon,
  MousePointerClick,
  Mountain,
  Snowflake,
  Waves,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

function Wordmark({ className }: { className?: string }) {
  // The wordmark SVG uses `currentColor`; a CSS mask lets it take any theme
  // color (bg-current = current text color) — readable on light or dark.
  return (
    <span
      role="img"
      aria-label="TerraTrain"
      className={cn("inline-block bg-current align-middle", className)}
      style={{
        maskImage: "url(/brand/wordmark.svg)",
        WebkitMaskImage: "url(/brand/wordmark.svg)",
        maskRepeat: "no-repeat",
        WebkitMaskRepeat: "no-repeat",
        maskSize: "contain",
        WebkitMaskSize: "contain",
        maskPosition: "center",
        WebkitMaskPosition: "center",
        aspectRatio: "1233.67 / 200.89",
      }}
    />
  );
}

function Lockup({ wordmarkClass }: { wordmarkClass?: string }) {
  return (
    <span className="flex items-center gap-2">
      <img src="/brand/mark.svg" alt="" className="h-7 w-auto" />
      <Wordmark className={cn("h-4 text-text", wordmarkClass)} />
    </span>
  );
}

const SPORTS = [
  { icon: Bike, label: "Radsport" },
  { icon: Footprints, label: "Laufen" },
  { icon: Waves, label: "Schwimmen" },
  { icon: Snowflake, label: "Langlauf" },
  { icon: Dumbbell, label: "Krafttraining" },
];

const FEATURES = [
  {
    icon: LineChart,
    title: "Dashboard",
    desc: "CTL, ATL und Form (TSB) aus deinen echten Intervals.icu-Daten — auf einen Blick.",
    shot: "/shots/dashboard.jpg",
  },
  {
    icon: Brain,
    title: "KI-Coach",
    desc: "Strukturierte Einzel-Workouts, abgestimmt auf Form, Ziel und die Topografie deiner Route.",
    shot: "/shots/coach.jpg",
  },
  {
    icon: Calendar,
    title: "Wochenplaner",
    desc: "Ganze Trainingswochen mit Periodisierung (Belastung/Erholung) – automatisch generiert.",
    shot: "/shots/planner.jpg",
  },
  {
    icon: MapIcon,
    title: "Routen & Terrain",
    desc: "GPX hochladen, Anstiege analysieren – Intervalle werden genau auf die Berge gelegt.",
    shot: "/shots/routes.jpg",
  },
  {
    icon: Dumbbell,
    title: "Workouts",
    desc: "Bearbeiten, „Press Lap“ setzen und mit einem Klick zu Intervals.icu pushen.",
    shot: "/shots/workouts.jpg",
  },
  {
    icon: BookOpen,
    title: "Wissensbasis",
    desc: "Lade Trainingsliteratur hoch – der Coach plant fundierter dank RAG.",
    shot: "/shots/knowledge.jpg",
  },
];

const STEPS = [
  {
    icon: Link2,
    title: "Verbinden",
    desc: "Verknüpfe dein Intervals.icu-Konto. Deine Leistungs- und Gesundheitsdaten bleiben deine.",
  },
  {
    icon: Brain,
    title: "Planen lassen",
    desc: "Der KI-Coach erstellt sport- und terrain-spezifische Workouts – auf deine Form abgestimmt.",
  },
  {
    icon: MousePointerClick,
    title: "Pushen & fahren",
    desc: "Workout prüfen, anpassen und direkt auf dein Gerät zu Intervals.icu senden.",
  },
];

export default function MarketingPage() {
  const { user, status, bootstrap } = useAuthStore();

  useEffect(() => {
    if (status === "idle") void bootstrap();
  }, [status, bootstrap]);

  const authed = status === "authenticated" && !!user;
  const primaryHref = authed ? "/dashboard" : "/login";
  const primaryLabel = authed ? "Zum Dashboard" : "Kostenlos starten";

  return (
    <div className="min-h-screen bg-bg text-text">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Lockup />
          <nav className="hidden items-center gap-8 text-sm text-text-secondary sm:flex">
            <a href="#features" className="transition-colors hover:text-text">Funktionen</a>
            <a href="#how" className="transition-colors hover:text-text">So funktioniert&apos;s</a>
            <a href="#sports" className="transition-colors hover:text-text">Sportarten</a>
          </nav>
          <Link
            href={primaryHref}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
          >
            {authed ? "Dashboard" : "Anmelden"}
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* lime glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-[-10rem] h-[28rem] w-[48rem] -translate-x-1/2 rounded-full opacity-20 blur-3xl"
          style={{ background: "radial-gradient(closest-side, var(--color-accent), transparent)" }}
        />
        <div className="relative mx-auto max-w-4xl px-5 pt-20 pb-14 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-text-secondary">
            <Mountain className="h-3.5 w-3.5 text-accent" />
            KI-Coaching, abgestimmt auf dein Terrain
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            Dein Ausdauertraining,{" "}
            <span className="text-accent">intelligent geplant</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-text-secondary sm:text-lg">
            TerraTrain verbindet deine echten Trainingsdaten mit GPX-Streckenanalyse und einem
            KI-Coach – für strukturierte Workouts über fünf Sportarten hinweg, direkt in Intervals.icu.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href={primaryHref}
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
            >
              {primaryLabel}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-5 py-3 text-sm font-medium text-text transition-colors hover:bg-surface-2"
            >
              Funktionen ansehen
            </a>
          </div>

          {/* Hero screenshot */}
          <div className="relative mx-auto mt-14 max-w-4xl">
            <div className="overflow-hidden rounded-xl border border-border-strong bg-surface shadow-2xl">
              <div className="flex items-center gap-1.5 border-b border-border bg-surface-2 px-4 py-2.5">
                <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
                <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
                <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              </div>
              <img src="/shots/dashboard.jpg" alt="TerraTrain Dashboard" className="w-full" />
            </div>
          </div>
        </div>
      </section>

      {/* Sports */}
      <section id="sports" className="border-y border-border/60 bg-surface/40">
        <div className="mx-auto max-w-5xl px-5 py-10">
          <p className="text-center text-xs uppercase tracking-widest text-text-muted">
            Eine App für fünf Sportarten – mit sportartgerechten Trainingszonen
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {SPORTS.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-text-secondary">
                <Icon className="h-5 w-5 text-accent" />
                <span className="text-sm font-medium">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-5 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Alles für strukturiertes Training
          </h2>
          <p className="mt-3 text-text-secondary">
            Von der Formanalyse bis zum fertigen Wochenplan – TerraTrain deckt den kompletten
            Coaching-Zyklus ab.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc, shot }) => (
            <div
              key={title}
              className="group overflow-hidden rounded-xl border border-border bg-surface transition-colors hover:border-border-strong"
            >
              <div className="aspect-[16/10] overflow-hidden border-b border-border">
                <img
                  src={shot}
                  alt={title}
                  className="h-full w-full object-cover object-top transition-transform duration-500 group-hover:scale-105"
                />
              </div>
              <div className="p-5">
                <div className="flex items-center gap-2">
                  <Icon className="h-4.5 w-4.5 text-accent" />
                  <h3 className="text-sm font-semibold">{title}</h3>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-5xl px-5 py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">In drei Schritten</h2>
            <p className="mt-3 text-text-secondary">
              Von der Anmeldung bis zum ersten Workout auf deinem Gerät.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, desc }, i) => (
              <div key={title} className="rounded-xl border border-border bg-surface p-6">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="text-xs font-semibold text-text-muted">
                    Schritt {i + 1}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-4xl px-5 py-24 text-center">
        <Gauge className="mx-auto h-10 w-10 text-accent" />
        <h2 className="mx-auto mt-5 max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
          Bereit, smarter zu trainieren?
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-text-secondary">
          Verbinde dein Intervals.icu-Konto und lass den KI-Coach deinen nächsten Block planen.
        </p>
        <Link
          href={primaryHref}
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
        >
          {primaryLabel}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row">
          <Lockup />
          <p className="text-xs text-text-muted">
            © {"2026"} TerraTrain · KI-Coaching für Ausdauersport
          </p>
        </div>
      </footer>
    </div>
  );
}
