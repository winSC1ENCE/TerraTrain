"use client";

import { MobileTabBar, Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 pb-20 md:pb-8 lg:p-8">
          {children}
        </main>
      </div>
      <MobileTabBar />
    </div>
  );
}
