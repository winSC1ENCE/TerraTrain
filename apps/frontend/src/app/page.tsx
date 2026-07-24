"use client";

import { useEffect, useState } from "react";
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
  Globe,
  LineChart,
  Link2,
  Lock,
  Map as MapIcon,
  MousePointerClick,
  Mountain,
  Snowflake,
  Waves,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useAthleteStore } from "@/stores/athlete-store";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";

function Wordmark({ className }: { className?: string }) {
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

export default function MarketingPage() {
  const { user, status, bootstrap } = useAuthStore();
  const { language, setLanguage } = useAthleteStore();
  const t = useT();
  const lang = t.landing;

  const [showDevModal, setShowDevModal] = useState(false);

  useEffect(() => {
    if (status === "idle") void bootstrap();
  }, [status, bootstrap]);

  const authed = status === "authenticated" && !!user;

  const SPORTS = [
    { icon: Bike, label: lang.sports.cycling },
    { icon: Footprints, label: lang.sports.running },
    { icon: Waves, label: lang.sports.swimming },
    { icon: Snowflake, label: lang.sports.skiing },
    { icon: Dumbbell, label: lang.sports.strength },
  ];

  const FEATURES = [
    {
      icon: LineChart,
      title: lang.features.dashboardTitle,
      desc: lang.features.dashboardDesc,
      shot: "/shots/dashboard.jpg",
    },
    {
      icon: Brain,
      title: lang.features.coachTitle,
      desc: lang.features.coachDesc,
      shot: "/shots/coach.jpg",
    },
    {
      icon: Calendar,
      title: lang.features.plannerTitle,
      desc: lang.features.plannerDesc,
      shot: "/shots/planner.jpg",
    },
    {
      icon: MapIcon,
      title: lang.features.routesTitle,
      desc: lang.features.routesDesc,
      shot: "/shots/routes.jpg",
    },
    {
      icon: Dumbbell,
      title: lang.features.workoutsTitle,
      desc: lang.features.workoutsDesc,
      shot: "/shots/workouts.jpg",
    },
    {
      icon: BookOpen,
      title: lang.features.knowledgeTitle,
      desc: lang.features.knowledgeDesc,
      shot: "/shots/knowledge.jpg",
    },
  ];

  const STEPS = [
    {
      icon: Link2,
      title: lang.steps.s1Title,
      desc: lang.steps.s1Desc,
    },
    {
      icon: Brain,
      title: lang.steps.s2Title,
      desc: lang.steps.s2Desc,
    },
    {
      icon: MousePointerClick,
      title: lang.steps.s3Title,
      desc: lang.steps.s3Desc,
    },
  ];

  function handleLoginClick(e: React.MouseEvent) {
    if (!authed) {
      e.preventDefault();
      setShowDevModal(true);
    }
  }

  return (
    <div className="min-h-screen bg-bg text-text">
      {/* Development Banner */}
      <div className="bg-accent/15 border-b border-accent/30 py-2 px-4 text-center text-xs text-accent font-medium flex items-center justify-center gap-2">
        <Lock className="h-3.5 w-3.5" />
        <span>{lang.hero.devNoticeBadge} — {lang.hero.devNoticeMessage}</span>
      </div>

      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Lockup />

          <nav className="hidden items-center gap-8 text-sm text-text-secondary sm:flex">
            <a href="#features" className="transition-colors hover:text-text">{lang.nav.features}</a>
            <a href="#how" className="transition-colors hover:text-text">{lang.nav.how}</a>
            <a href="#sports" className="transition-colors hover:text-text">{lang.nav.sports}</a>
          </nav>

          <div className="flex items-center gap-3">
            {/* Language Switcher */}
            <div className="flex items-center rounded-lg border border-border bg-surface p-1 text-xs">
              <button
                type="button"
                onClick={() => setLanguage("de")}
                className={cn(
                  "px-2 py-0.5 rounded font-medium transition-colors",
                  language === "de"
                    ? "bg-accent text-on-accent font-bold"
                    : "text-text-muted hover:text-text"
                )}
              >
                DE
              </button>
              <button
                type="button"
                onClick={() => setLanguage("en")}
                className={cn(
                  "px-2 py-0.5 rounded font-medium transition-colors",
                  language === "en"
                    ? "bg-accent text-on-accent font-bold"
                    : "text-text-muted hover:text-text"
                )}
              >
                EN
              </button>
            </div>

            {authed ? (
              <Link
                href="/dashboard"
                className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
              >
                Dashboard
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLoginClick}
                className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover flex items-center gap-1.5"
              >
                <Lock className="h-3.5 w-3.5" />
                {lang.nav.login}
              </button>
            )}
          </div>
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
            {lang.hero.badge}
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            {lang.hero.titleStart}
            <span className="text-accent">{lang.hero.titleHighlight}</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-text-secondary sm:text-lg">
            {lang.hero.subtitle}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            {authed ? (
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
              >
                Zum Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLoginClick}
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
              >
                {lang.hero.ctaPrimary}
                <ArrowRight className="h-4 w-4" />
              </button>
            )}
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-5 py-3 text-sm font-medium text-text transition-colors hover:bg-surface-2"
            >
              {lang.hero.ctaSecondary}
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
            {lang.sportsHeader}
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
            {lang.featuresTitle}
          </h2>
          <p className="mt-3 text-text-secondary">
            {lang.featuresSubtitle}
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
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">{lang.howTitle}</h2>
            <p className="mt-3 text-text-secondary">{lang.howSubtitle}</p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, desc }, i) => (
              <div key={title} className="rounded-xl border border-border bg-surface p-6">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="text-xs font-semibold text-text-muted">
                    {lang.steps.stepPrefix} {i + 1}
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
          {lang.ctaTitle}
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-text-secondary">
          {lang.ctaSubtitle}
        </p>
        <button
          type="button"
          onClick={handleLoginClick}
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-hover"
        >
          {lang.ctaButton}
          <ArrowRight className="h-4 w-4" />
        </button>
      </section>

      {/* Development Notice Modal */}
      {showDevModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2 text-accent">
                <Lock className="h-5 w-5" />
                <h3 className="font-bold text-base text-text">{lang.devModalTitle}</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowDevModal(false)}
                className="text-text-muted hover:text-text p-1 rounded-md transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">
              {lang.devModalDesc}
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Link
                href="/login"
                onClick={() => setShowDevModal(false)}
                className="px-3 py-1.5 text-xs text-text-muted hover:text-text transition-colors"
              >
                (Entwickler Login)
              </Link>
              <Button onClick={() => setShowDevModal(false)} className="px-4 py-2 text-xs">
                {lang.devModalClose}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row">
          <Lockup />
          <p className="text-xs text-text-muted">
            {lang.footer}
          </p>
        </div>
      </footer>
    </div>
  );
}
