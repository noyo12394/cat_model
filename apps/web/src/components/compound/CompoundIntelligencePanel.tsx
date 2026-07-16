"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Binoculars,
  BrainCircuit,
  CheckCircle2,
  CircleDashed,
  GitBranch,
  Microscope,
  Radar,
  Satellite,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { CompoundEventSummary, EvidenceChannel } from "@/lib/types";

const TABS = ["Fusion", "Possible futures", "Evidence", "Next check"] as const;
type Tab = (typeof TABS)[number];

export function CompoundIntelligencePanel({ eventId }: { eventId: string }) {
  const [tab, setTab] = useState<Tab>("Fusion");
  const setPanel = useAppStore((s) => s.setPanel);
  const setOffsetMinutes = useAppStore((s) => s.setOffsetMinutes);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["multi-hazard-overview"],
    queryFn: api.multiHazardOverview,
    staleTime: 60_000,
  });

  if (isLoading) return <div className="panel-stack panel-skeleton"><span /><span /><span /></div>;
  if (isError || !data) return <div className="panel-empty"><TriangleAlert size={22} /><strong>Compound intelligence unavailable</strong><span>The existing incident and source-health views remain available.</span></div>;

  const event = data.compound_events.find((item) => item.event_id === eventId) ?? data.compound_events[0];
  if (!event) return <div className="panel-empty"><CircleDashed size={22} /><strong>No compound event selected</strong></div>;

  return (
    <div className="compound-panel">
      <header className="compound-header">
        <div className="compound-title-row">
          <span className="compound-icon"><BrainCircuit size={18} aria-hidden /></span>
          <div><span className="panel-kicker">COMPOUND INTELLIGENCE</span><h1>{event.title}</h1></div>
          <span className="research-pill">RESEARCH DEMO</span>
        </div>
        <p>{event.fusion_explanation}</p>
        <div className="fusion-status-row">
          <span><i className="feed-dot live" /> {data.live_feed_count} live feeds reachable</span>
          <span><i className="feed-dot demo" /> {data.demo_feed_count} demo</span>
          <span><i className="feed-dot unavailable" /> {data.unavailable_feed_count} unavailable</span>
        </div>
      </header>

      <div className="compound-tabs" role="tablist" aria-label="Compound intelligence views">
        {TABS.map((item) => (
          <button key={item} type="button" role="tab" aria-selected={tab === item} className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>{item}</button>
        ))}
      </div>

      <div className="compound-content">
        {tab === "Fusion" && <FusionView event={event} />}
        {tab === "Possible futures" && <FuturesView event={event} onSelectTime={setOffsetMinutes} />}
        {tab === "Evidence" && <EvidenceView event={event} />}
        {tab === "Next check" && <NextCheckView event={event} />}
      </div>

      <footer className="compound-footer">
        <p>{data.research_notice}</p>
        <button type="button" onClick={() => setPanel({ kind: "incident", incidentId: "developing-flood-bethlehem" })}>Open full incident room <ArrowRight size={14} /></button>
      </footer>
    </div>
  );
}

function FusionView({ event }: { event: CompoundEventSummary }) {
  return (
    <div className="compound-view-stack">
      <section>
        <div className="compound-section-heading"><div><span className="panel-kicker">SIGNALS FUSED</span><h2>One developing event</h2></div><span className="confidence-label">{event.fusion_confidence} confidence</span></div>
        <div className="signal-fusion-row">
          {event.signals.map((signal, index) => (
            <div key={signal.signal_id} className={`signal-card hazard-${hazardGroup(signal.hazard_type)}`}>
              {index > 0 && <span className="fusion-plus" aria-hidden>+</span>}
              <span className="signal-glyph">{hazardGlyph(signal.hazard_type)}</span>
              <strong>{signal.label}</strong>
              <small>{signal.source}</small>
              <span className={`data-state ${signal.data_status}`}>{signal.data_status}</span>
            </div>
          ))}
        </div>
        <div className="matched-row">Matched on {event.matched_on.map((item) => <span key={item}>{item}</span>)}</div>
      </section>

      <section className="consequence-lens-section">
        <div className="compound-section-heading"><div><span className="panel-kicker">CONSEQUENCE LENS</span><h2>From signal to service impact</h2></div></div>
        <ol className="consequence-chain">
          {event.consequence_chain.map((step, index) => (
            <li key={step.step_id} className={`certainty-${step.certainty}`}>
              <span className="chain-index">{index + 1}</span>
              <div><div className="chain-meta"><span>{step.certainty.replace("_", " ")}</span><span>{step.time_window}</span></div><strong>{step.label}</strong><p>{step.detail}</p><small>Confidence: {step.confidence}</small></div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function FuturesView({ event, onSelectTime }: { event: CompoundEventSummary; onSelectTime: (minutes: number) => void }) {
  const offsets = [60, 180, 360];
  return (
    <div className="compound-view-stack">
      <div className="future-intro"><GitBranch size={18} /><div><strong>Several futures, not one answer</strong><p>These branches are qualitative research-demo scenarios, not calibrated probabilities.</p></div></div>
      <div className="future-branches">
        {event.possible_futures.map((future, index) => (
          <button key={future.future_id} type="button" className={`future-card ${future.support}`} onClick={() => onSelectTime(offsets[index] ?? 180)}>
            <div className="future-card-top"><span>{supportLabel(future.support)}</span><ArrowRight size={14} /></div>
            <strong>{future.label}</strong><p>{future.detail}</p>
            <div className="future-consequence"><span>Possible consequence</span>{future.consequence}</div>
            <small><Radar size={12} /> Watch for: {future.distinguishing_signal}</small>
          </button>
        ))}
      </div>
    </div>
  );
}

function EvidenceView({ event }: { event: CompoundEventSummary }) {
  return (
    <div className="compound-view-stack">
      <div className="evidence-intro"><Microscope size={18} /><div><strong>Evidence Agreement</strong><p>Compare independent channels before trusting a consequence.</p></div></div>
      <div className="agreement-grid">
        {event.evidence_agreement.map((channel) => <EvidenceRow key={channel.channel} channel={channel} />)}
      </div>
      <section className="limitations-card"><span className="panel-kicker">MODEL TRUST</span><h2>What this view cannot establish</h2><ul>{event.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </div>
  );
}

function EvidenceRow({ channel }: { channel: EvidenceChannel }) {
  const Icon = channel.channel.includes("Satellite") ? Satellite : channel.agreement === "supports" ? CheckCircle2 : CircleDashed;
  return <div className={`agreement-row ${channel.agreement}`}><span className="agreement-icon"><Icon size={16} /></span><div><strong>{channel.channel}</strong><p>{channel.detail}</p></div><span className="agreement-state">{channel.agreement}</span></div>;
}

function NextCheckView({ event }: { event: CompoundEventSummary }) {
  return (
    <div className="compound-view-stack">
      <div className="next-check-intro"><Binoculars size={18} /><div><strong>What should we check next?</strong><p>Prioritized by expected reduction in uncertainty—not by drama or visual appeal.</p></div></div>
      <ol className="verification-list">
        {event.next_checks.map((item) => (
          <li key={item.rank}><span className="verification-rank">{item.rank}</span><div><strong>{item.label}</strong><p>{item.why}</p><span>{item.expected_value}</span><button type="button" disabled title="Research workflow preview">{item.action}</button></div></li>
        ))}
      </ol>
      <p className="preview-note"><ShieldAlert size={13} /> Actions are disabled until approved imagery, camera, and field-workflow integrations are configured.</p>
    </div>
  );
}

function hazardGroup(type: string): string {
  if (type.includes("weather")) return "weather";
  if (type.includes("flood")) return "flood";
  if (type.includes("landslide")) return "landslide";
  return "other";
}

function hazardGlyph(type: string): string {
  if (type.includes("weather")) return "RAIN";
  if (type.includes("flood")) return "RIVER";
  if (type.includes("landslide")) return "SOIL";
  return "DATA";
}

function supportLabel(value: string): string {
  return value === "most_supported" ? "MOST SUPPORTED" : value === "plausible" ? "PLAUSIBLE" : "STRESS CASE";
}
