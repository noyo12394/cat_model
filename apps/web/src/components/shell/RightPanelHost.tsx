"use client";

import { useAppStore } from "@/lib/store";
import { RegionSummaryPanel } from "./RegionSummaryPanel";
import { LocationCapsulePanel } from "@/components/capsule/LocationCapsulePanel";
import { IncidentRoomPanel } from "@/components/incident/IncidentRoomPanel";
import { RouteRiskPanel } from "@/components/route/RouteRiskPanel";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { RiskModelPanel } from "@/components/scenario/RiskModelPanel";
import { PortfolioPanel } from "@/components/portfolio/PortfolioPanel";
import { HiddenRisksPanel } from "@/components/common/HiddenRisksPanel";
import { SourceHealthPanel } from "@/components/common/SourceHealthPanel";
import { CompoundIntelligencePanel } from "@/components/compound/CompoundIntelligencePanel";
import { CommunityPanel } from "@/components/community/CommunityPanel";
import { GlobalEventsPanel } from "@/components/global/GlobalEventsPanel";

/** The right intelligence panel (section 6.3): content changes based on
 * context - no selection, place selected, event selected, route selected,
 * scenario selected, or a question asked. */
export function RightPanelHost() {
  const mode = useAppStore((s) => s.mode);
  const panel = useAppStore((s) => s.panel);

  if (mode === "scenario-lab") return <RiskModelPanel />;
  if (mode === "portfolio") return <PortfolioPanel />;

  switch (panel.kind) {
    case "global-events":
      return <GlobalEventsPanel />;
    case "compound":
      return <CompoundIntelligencePanel eventId={panel.eventId} />;
    case "place":
      return <LocationCapsulePanel placeId={panel.placeId} />;
    case "incident":
      return <IncidentRoomPanel incidentId={panel.incidentId} />;
    case "route":
      return <RouteRiskPanel originPlaceId={panel.originPlaceId} destinationPlaceId={panel.destinationPlaceId} />;
    case "assistant":
      return <AssistantPanel question={panel.question} />;
    case "community":
      return <CommunityPanel view={panel.view} incidentId={panel.incidentId} />;
    case "hidden-risks":
      return <HiddenRisksPanel />;
    case "source-health":
      return <SourceHealthPanel />;
    default:
      return <RegionSummaryPanel />;
  }
}
