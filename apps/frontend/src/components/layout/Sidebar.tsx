"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Brain,
  Calendar,
  Dumbbell,
  LayoutDashboard,
  Map,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

export function Sidebar() {
  const pathname = usePathname();
  const t = useT();

  const items = [
    { href: "/", label: t.nav.dashboard, icon: LayoutDashboard },
    { href: "/coach", label: t.nav.coach, icon: Brain },
    { href: "/weekly-planner", label: t.nav.weeklyPlanner, icon: Calendar },
    { href: "/routes", label: t.nav.routes, icon: Map },
    { href: "/workouts", label: t.nav.workouts, icon: Dumbbell },
    { href: "/knowledge", label: t.nav.knowledge, icon: BookOpen },
    { href: "/settings", label: t.nav.settings, icon: Settings },
  ];

  return (
    <aside className="hidden md:flex flex-col w-16 lg:w-60 shrink-0 border-r border-border bg-surface min-h-screen sticky top-0">
      <div className="flex items-center gap-2.5 px-4 lg:px-5 h-14 border-b border-border">
        <img src="/terratrain_icon.svg" alt="TerraTrain Icon" className="h-6 w-6 shrink-0" />
        <span className="hidden lg:block text-sm font-bold tracking-tight">
          TerraTrain
        </span>
      </div>
      <nav className="flex flex-col gap-0.5 p-2 lg:p-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors border-l-2",
                active
                  ? "border-accent bg-surface-2 text-text font-medium"
                  : "border-transparent text-text-muted hover:text-text-secondary hover:bg-surface-2/50"
              )}
            >
              <Icon className="h-4.5 w-4.5 shrink-0" style={{ width: 18, height: 18 }} />
              <span className="hidden lg:block">{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileTabBar() {
  const pathname = usePathname();
  const t = useT();

  const items = [
    { href: "/", label: t.nav.dashboard, icon: LayoutDashboard },
    { href: "/coach", label: t.nav.coach, icon: Brain },
    { href: "/weekly-planner", label: t.nav.weeklyPlanner, icon: Calendar },
    { href: "/routes", label: t.nav.routes, icon: Map },
    { href: "/workouts", label: t.nav.workouts, icon: Dumbbell },
    { href: "/knowledge", label: t.nav.knowledge, icon: BookOpen },
    { href: "/settings", label: t.nav.settings, icon: Settings },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 flex justify-around border-t border-border bg-surface py-1.5">
      {items.map(({ href, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "rounded-lg p-2.5",
              active ? "text-accent" : "text-text-muted"
            )}
          >
            <Icon style={{ width: 20, height: 20 }} />
          </Link>
        );
      })}
    </nav>
  );
}
