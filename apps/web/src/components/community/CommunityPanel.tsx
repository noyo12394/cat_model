"use client";

import { useState } from "react";
import { HeartPulse, MessageCircleWarning } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { CommunityPulsePanel } from "./CommunityPulsePanel";
import { CommunitySignalsPanel } from "./CommunitySignalsPanel";

export type CommunityView = "sentiment" | "signals";

/** One "Community" surface with two scoped views:
 *  - Local sentiment: deterministic concern index over incident-level reports.
 *  - Global signals: source-gated public posts for a selected GDACS event.
 * Consolidated from two separate nav tabs so the crowd-signal tools live in
 * one place instead of competing for nav space. */
export function CommunityPanel({ view, incidentId }: { view: CommunityView; incidentId: string }) {
  const [active, setActive] = useState<CommunityView>(view);
  const setMapScope = useAppStore((s) => s.setMapScope);

  const select = (next: CommunityView) => {
    setActive(next);
    setMapScope(next === "signals" ? "global" : "local");
  };

  return (
    <div className="community-wrap">
      <div className="community-switch" role="tablist" aria-label="Community views">
        <button type="button" role="tab" aria-selected={active === "sentiment"} className={active === "sentiment" ? "is-active" : ""} onClick={() => select("sentiment")}>
          <HeartPulse size={14} aria-hidden /> Local sentiment
        </button>
        <button type="button" role="tab" aria-selected={active === "signals"} className={active === "signals" ? "is-active" : ""} onClick={() => select("signals")}>
          <MessageCircleWarning size={14} aria-hidden /> Global signals
        </button>
      </div>
      <div className="community-wrap-body">
        {active === "sentiment" ? <CommunityPulsePanel incidentId={incidentId} /> : <CommunitySignalsPanel />}
      </div>
    </div>
  );
}
