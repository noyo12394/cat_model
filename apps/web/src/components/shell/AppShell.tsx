"use client";

import { useAppStore } from "@/lib/store";
import { Activity, Bot, Eye, Radio } from "lucide-react";
import { TopSearchBar } from "./TopSearchBar";
import { LeftNavRail } from "./LeftNavRail";
import { RightPanelHost } from "./RightPanelHost";
import { BottomTimeBar } from "./BottomTimeBar";
import { MapControls } from "./MapControls";
import { MapView } from "@/components/map/MapView";
import { TrustFooter } from "@/components/common/TrustFooter";

/** The persistent application shell (section 6): search bar, nav rail, map,
 * right intelligence panel, and time bar. Lives in the root layout so the
 * map instance survives client-side navigation between modes/incidents. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const uncertaintyLens = useAppStore((s) => s.uncertaintyLens);
  const highContrast = useAppStore((s) => s.highContrast);
  const setPanel = useAppStore((s) => s.setPanel);
  const mapScope = useAppStore((s) => s.mapScope);

  return (
    <div className={`earthpulse-shell flex h-dvh flex-col ${highContrast ? "high-contrast" : ""}`}>
      <a href="#earthpulse-map" className="skip-link">Skip to map</a>
      <a href="#intelligence-panel" className="skip-link">Skip to intelligence</a>

      <header className="app-header">
        <div className="brand-lockup" aria-label="EarthPulse home">
          <span className="brand-mark" aria-hidden><Activity size={18} strokeWidth={2.5} /></span>
          <span className="brand-name">Earth<span>Pulse</span></span>
          <span className="brand-edition">LIVE INTELLIGENCE</span>
        </div>
        <TopSearchBar />
        <div className="header-status" aria-label="System status">
          <span className="status-chip status-chip-live"><Radio size={13} aria-hidden /> Research demo</span>
          {uncertaintyLens && <span className="status-chip status-chip-lens"><Eye size={13} aria-hidden /> Uncertainty</span>}
        </div>
      </header>

      <div className="workspace flex flex-1 overflow-hidden">
        <LeftNavRail />
        <main id="earthpulse-map" className="map-stage relative flex-1" tabIndex={-1}>
          <MapView />
          <MapControls />

          <div className="map-context-card" role="status">
            <span className="context-eyebrow">{mapScope === "global" ? "LIVE EVENT MAP · TAP A SYMBOL" : "FLOOD SCENE · RESEARCH DEMO"}</span>
            <strong>{mapScope === "global" ? "Rings, waves, swirls: one symbol per hazard" : "Rain → river rise → crossing check"}</strong>
            <span>{mapScope === "global" ? "Icons identify the reported source location, not an impact footprint." : "Blue streaks show rainfall direction; cyan shows the modeled river corridor."}</span>
          </div>

          <button
            type="button"
            className="ask-earthpulse-button"
            onClick={() => setPanel({
              kind: "assistant",
              question: mapScope === "global"
                ? "Give a global GDACS brief for the current operating window. Explain what should be verified first and the limits of the watch score."
                : "Explain the compound event and what we should check next",
            })}
          >
            <Bot size={17} aria-hidden />
            <span><strong>Ask EarthPulse</strong><small>{mapScope === "global" ? "Live global events" : "Grounded agent"}</small></span>
          </button>

          <aside
            id="intelligence-panel"
            className="intelligence-panel"
            aria-label="Intelligence panel"
            tabIndex={-1}
          >
            <RightPanelHost />
          </aside>

          <BottomTimeBar />
        </main>
      </div>
      <TrustFooter />
      {children}
    </div>
  );
}
