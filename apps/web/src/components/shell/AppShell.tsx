"use client";

import { useAppStore } from "@/lib/store";
import { TopSearchBar } from "./TopSearchBar";
import { LeftNavRail } from "./LeftNavRail";
import { RightPanelHost } from "./RightPanelHost";
import { BottomTimeBar } from "./BottomTimeBar";
import { MapView } from "@/components/map/MapView";
import { TrustFooter } from "@/components/common/TrustFooter";

/** The persistent application shell (section 6): search bar, nav rail, map,
 * right intelligence panel, and time bar. Lives in the root layout so the
 * map instance survives client-side navigation between modes/incidents. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const uncertaintyLens = useAppStore((s) => s.uncertaintyLens);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center gap-3 border-b border-border bg-surface px-3 py-2">
        <span className="shrink-0 text-base font-semibold tracking-tight">
          Earth<span className="text-accent">Pulse</span>
        </span>
        <TopSearchBar />
        {uncertaintyLens && (
          <span className="ml-auto rounded-full border border-dashed border-accent px-2 py-0.5 text-xs text-accent">
            Uncertainty lens on
          </span>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        <LeftNavRail />
        <main className="relative flex-1">
          <MapView />
        </main>
        <aside
          className="hidden w-[420px] shrink-0 overflow-y-auto border-l border-border bg-surface md:block"
          aria-label="Intelligence panel"
        >
          <RightPanelHost />
        </aside>
      </div>

      {/* Mobile: render the panel below the map instead of hiding it. */}
      <div className="max-h-[45vh] overflow-y-auto border-t border-border bg-surface md:hidden">
        <RightPanelHost />
      </div>

      <BottomTimeBar />
      <TrustFooter />
      {children}
    </div>
  );
}
