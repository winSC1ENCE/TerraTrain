"use client";

import { AthleteGate } from "@/components/layout/AthleteGate";
import { AppShell } from "@/components/layout/AppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AthleteGate>
      <AppShell>{children}</AppShell>
    </AthleteGate>
  );
}
