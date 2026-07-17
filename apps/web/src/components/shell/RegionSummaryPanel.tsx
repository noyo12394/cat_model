"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BrainCircuit, ChevronRight, Clock3, CloudRain, Gauge, Globe2, Hospital, MessagesSquare, Route, ShieldAlert, Sparkles, Waves } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DisasterHeartbeat } from "@/components/common/DisasterHeartbeat";

export function RegionSummaryPanel() {
  const { data: summary, isLoading, isError } = useQuery({ queryKey: ["live-summary"], queryFn: api.liveSummary });
  const { data: multiHazard } = useQuery({ queryKey: ["multi-hazard-overview"], queryFn: api.multiHazardOverview, staleTime: 60_000 });
  const setPanel = useAppStore((s) => s.setPanel);
  const setOffsetMinutes = useAppStore((s) => s.setOffsetMinutes);
  const flyTo = useAppStore((s) => s.flyTo);
  const setMapScope = useAppStore((s) => s.setMapScope);
  const savedPlaces = useAppStore((s) => s.savedPlaces);

  function openIncident(offset = 0) {
    setPanel({ kind: "incident", incidentId: "developing-flood-bethlehem" });
    setOffsetMinutes(offset);
    flyTo([-75.3705, 40.6259], 13);
  }

  function openCompound() {
    setPanel({ kind: "compound", eventId: "compound-flood-access-bethlehem" });
    flyTo([-75.3705, 40.6259], 13);
  }

  if (isLoading) return <PanelSkeleton />;
  if (isError || !summary) return (
    <div className="panel-empty"><ShieldAlert size={22} /><strong>Regional summary unavailable</strong><span>The map remains available. Check Source Health for details.</span><button type="button" onClick={() => setPanel({ kind: "source-health" })}>Open source health</button></div>
  );

  return (
    <div className="region-panel panel-stack">
      <div className="panel-header-row">
        <div>
          <span className="panel-kicker">REGIONAL PULSE</span>
          <h1>{summary.region_label}</h1>
        </div>
        <span className="demo-pill"><span /> DEMO</span>
      </div>

      <section className="primary-incident-card">
        <div className="incident-card-topline">
          <span className="severity-label"><BrainCircuit size={14} aria-hidden /> COMPOUND EVENT · DEMO</span>
          <span className="updated-label"><Clock3 size={12} aria-hidden /> just updated</span>
        </div>
        <h2>Rainfall, river rise, and access pressure</h2>
        <p>Three signals overlap in place and time. The concern is their shared effect on a limited set of river crossings—not one unexplained risk score.</p>
        <div className="signal-chip-row" aria-label="Signals fused into this event">
          <span><CloudRain size={13} aria-hidden /> Heavy rain</span><i>+</i>
          <span><Waves size={13} aria-hidden /> Rising river</span><i>+</i>
          <span><Gauge size={13} aria-hidden /> Wet ground</span>
        </div>
        <button type="button" className="primary-action" onClick={openCompound}>
          Open Compound Intelligence <ArrowUpRight size={16} aria-hidden />
        </button>
      </section>

      <section className="panel-section">
        <div className="section-heading-row"><div><span className="panel-kicker">NEXT 1–3 HOURS</span><h2>Possible impact sequence</h2></div><button type="button" onClick={() => openIncident(180)}>View outlook</button></div>
        <ol className="impact-sequence">
          <li><span className="sequence-index observed">1</span><div><strong>River continues rising</strong><small>Observed trend · high confidence</small></div></li>
          <li><span className="sequence-line" aria-hidden /><span className="sequence-index forecast">2</span><div><strong>Low crossing may be affected</strong><small>Forecast · moderate confidence</small></div></li>
          <li><span className="sequence-line" aria-hidden /><span className="sequence-index inferred">3</span><div><strong>Hospital travel time may increase</strong><small>AI-inferred · moderate confidence</small></div></li>
        </ol>
      </section>

      <section className="impact-metrics" aria-label="Regional impact summary">
        <button type="button" onClick={openCompound}><span className="metric-icon coral"><BrainCircuit size={16} /></span><strong>3</strong><small>signals fused</small></button>
        <button type="button" onClick={() => openIncident(180)}><span className="metric-icon blue"><Route size={16} /></span><strong>2</strong><small>crossings watched</small></button>
        <button type="button" onClick={() => setPanel({ kind: "source-health" })}><span className="metric-icon violet"><Hospital size={16} /></span><strong>{multiHazard?.live_feed_count ?? "—"}</strong><small>live feeds reachable</small></button>
      </section>

      <DisasterHeartbeat
        label="Event heartbeat"
        severity="severe"
        components={{ hazardIntensity: 0.6, rateOfChange: 0.7, geographicSpread: 0.3, infrastructureStress: 0.5, populationExposure: 0.4, sourceAgreement: 0.65 }}
      />

      <section className="panel-section quick-actions">
        <span className="panel-kicker">EXPLORE</span>
        <button type="button" onClick={() => { setMapScope("global"); setPanel({ kind: "global-events" }); flyTo([8, 18], 1.45); }}><Globe2 size={16} /><span><strong>Global operational picture</strong><small>Live GDACS multi-hazard events</small></span><ChevronRight size={15} /></button>
        <button type="button" onClick={() => setPanel({ kind: "community-pulse", incidentId: "developing-flood-bethlehem" })}><MessagesSquare size={16} /><span><strong>Read the community pulse</strong><small>What people are reporting, signal vs. rumor</small></span><ChevronRight size={15} /></button>
        <button type="button" onClick={() => setPanel({ kind: "assistant", question: "What changed near Bethlehem in the last hour?" })}><Sparkles size={16} /><span><strong>What changed?</strong><small>Compare with one hour ago</small></span><ChevronRight size={15} /></button>
        <button type="button" onClick={openCompound}><BrainCircuit size={16} /><span><strong>Compare possible futures</strong><small>See what would distinguish each branch</small></span><ChevronRight size={15} /></button>
        <button type="button" onClick={() => setPanel({ kind: "hidden-risks" })}><ShieldAlert size={16} /><span><strong>Find hidden risks</strong><small>Single points of failure and weak data</small></span><ChevronRight size={15} /></button>
      </section>

      {savedPlaces.length > 0 && (
        <section className="panel-section saved-places"><span className="panel-kicker">SAVED PLACES</span>{savedPlaces.map((place) => <button key={place.place_id} type="button" onClick={() => { setPanel({ kind: "place", placeId: place.place_id }); flyTo(place.center, 14); }}><span>{place.name}</span><ChevronRight size={14} /></button>)}</section>
      )}
    </div>
  );
}

function PanelSkeleton() {
  return <div className="panel-stack panel-skeleton" aria-label="Loading regional intelligence"><span /><span /><span /><span /></div>;
}
