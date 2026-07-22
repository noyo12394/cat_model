"use client";

import { ArrowRight, CheckCircle2, Database, FlaskConical, MapPinned, Radio, Search, ShieldCheck } from "lucide-react";

type Props = {
  mode: "explore" | "model";
  placeName?: string;
  eventCount: number;
  eventStatus?: string;
  hasDemoResult: boolean;
  hasAnalysisResult: boolean;
  onFocusSearch: () => void;
  onOpenLive: () => void;
  onRunDemo: () => void;
  onOpenResults: () => void;
};

function statusLabel(status?: string) {
  if (status === "live") return "official feed connected";
  if (status === "unavailable") return "official feed unavailable";
  return "checking official feed";
}

export function WorkspaceMission({
  mode,
  placeName,
  eventCount,
  eventStatus,
  hasDemoResult,
  hasAnalysisResult,
  onFocusSearch,
  onOpenLive,
  onRunDemo,
  onOpenResults,
}: Props) {
  const hasResult = hasDemoResult || hasAnalysisResult;

  if (mode === "model") {
    return <aside className="workspace-mission model-mission" aria-label="Model workflow guide">
      <div className="mission-heading">
        <span className="mission-kicker"><FlaskConical size={14} /> Model workflow</span>
        <span className={placeName ? "mission-ready" : "mission-pending"}>{placeName ? "location ready" : "location required"}</span>
      </div>
      <h2>Run only what the evidence supports.</h2>
      <p>RiskChain keeps exposure screening, modelled loss, and live observations separate. A run never fills missing hazard intensity with a guess.</p>
      <ol className="model-path">
        <li className={placeName ? "complete" : "active"}><span>01</span><div><strong>Locate</strong><small>{placeName ?? "Search and select a source-backed location"}</small></div>{placeName ? <CheckCircle2 size={15} /> : <MapPinned size={15} />}</li>
        <li className="active"><span>02</span><div><strong>Set the scenario</strong><small>Choose a connected hazard and authoritative event or return period.</small></div><Database size={15} /></li>
        <li><span>03</span><div><strong>Inspect the output</strong><small>Read the audit before interpreting a loss or exposure result.</small></div><ShieldCheck size={15} /></li>
      </ol>
      {hasResult ? <button className="mission-primary" type="button" onClick={onOpenResults}><ShieldCheck size={16} /> Open latest result <ArrowRight size={15} /></button> : <button className="mission-secondary" type="button" onClick={onRunDemo}><FlaskConical size={16} /> Explore labelled flood demo <ArrowRight size={15} /></button>}
      <small className="mission-footnote">The sample demo uses modelled inputs. It is not a current incident or a property appraisal.</small>
    </aside>;
  }

  return <aside className="workspace-mission explore-mission" aria-label="Start a RiskChain workflow">
    <div className="mission-heading">
      <span className="mission-kicker"><Radio size={14} /> Start with a question</span>
      <span className={eventStatus === "live" ? "mission-ready" : "mission-pending"}>{statusLabel(eventStatus)}</span>
    </div>
    <h2>Three defensible ways in.</h2>
    <p>Choose a workflow based on the evidence you actually have—not on a generic risk score.</p>
    <div className="mission-options">
      <button type="button" onClick={onOpenLive}><Radio size={17} /><span><strong>What is happening now?</strong><small>{eventCount.toLocaleString()} official event{eventCount === 1 ? "" : "s"} currently visible</small></span><ArrowRight size={15} /></button>
      <button type="button" onClick={onFocusSearch}><Search size={17} /><span><strong>What can I analyse here?</strong><small>Locate an address, city, ZIP, or coordinates</small></span><ArrowRight size={15} /></button>
      <button type="button" onClick={onRunDemo}><FlaskConical size={17} /><span><strong>How does the model work?</strong><small>Open a labelled flood demonstration with curves and loss views</small></span><ArrowRight size={15} /></button>
    </div>
    <div className="mission-evidence"><ShieldCheck size={15} /><span><strong>Evidence rule</strong>Observed, officially reported, modelled, and demo data never share the same label.</span></div>
  </aside>;
}
