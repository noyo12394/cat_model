"use client";

import { ArrowRight, CheckCircle2, Database, FlaskConical, MapPinned, ShieldCheck } from "lucide-react";

type Props = {
  mode: "explore" | "model";
  placeName?: string;
  hasDemoResult: boolean;
  hasAnalysisResult: boolean;
  demoLoading: boolean;
  onRunDemo: () => void;
  onOpenResults: () => void;
};

export function WorkspaceMission({
  mode,
  placeName,
  hasDemoResult,
  hasAnalysisResult,
  demoLoading,
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
      {hasResult ? <button className="mission-primary" type="button" onClick={onOpenResults}><ShieldCheck size={16} /> Open latest result <ArrowRight size={15} /></button> : <button className="mission-secondary" type="button" onClick={onRunDemo} disabled={demoLoading}><FlaskConical size={16} /> {demoLoading ? "Starting demo…" : "Explore labelled flood demo"} <ArrowRight size={15} /></button>}
      <small className="mission-footnote">The sample demo uses modelled inputs. It is not a current incident or a property appraisal.</small>
    </aside>;
  }

  return <aside className="workspace-mission demo-mission" aria-label="Modelled demo, separate from event workspaces">
    <div className="mission-heading">
      <span className="mission-kicker"><FlaskConical size={14} /> Modelled demo</span>
      <span className="mission-modelled">Separate workspace</span>
    </div>
    <h2>See how the model works.</h2>
    <p>Open a labelled Bethlehem flood demonstration with curves, loss views, and a complete audit trail.</p>
    <div className="demo-separation-note"><ShieldCheck size={15} /><span><strong>Modelled inputs only</strong>This demonstration never appears as a Live or Historic event.</span></div>
    <button className="mission-secondary" type="button" onClick={onRunDemo} disabled={demoLoading}><FlaskConical size={16} /> {demoLoading ? "Starting modelled demo…" : "Open modelled demo"} <ArrowRight size={15} /></button>
    <small className="mission-footnote">Teaching example—not a current incident, observation, claim record, or property appraisal.</small>
  </aside>;
}
