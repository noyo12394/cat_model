"use client";

import type { FormEvent } from "react";
import { Activity, Bot, Box, CheckCircle2, Database, Eye, Layers3, MapPinned, Radio, Satellite, ShieldCheck, X } from "lucide-react";
import type { AnalysisRunResult, CopilotAnswer } from "@/lib/types";
import type { MapSelection, MapViewport } from "./RiskMap";

type LayerState = {
  events: boolean;
  analysis: boolean;
  demo: boolean;
  analysisOpacity: number;
};

type Props = {
  onClose: () => void;
  view: string;
  scope: "global" | "local";
  hazard: string;
  selection: MapSelection | null;
  viewport: MapViewport | null;
  visibleEventCount: number;
  analysisRun: AnalysisRunResult | null;
  hasDemoRun: boolean;
  layers: LayerState;
  onLayersChange: (next: LayerState) => void;
  question: string;
  onQuestionChange: (value: string) => void;
  answer: CopilotAnswer | null;
  loading: boolean;
  onSubmit: (event: FormEvent) => void;
};

const PROMPTS = [
  "Analyze the selected place with the connected CAT data",
  "Explain what is visible on the map",
  "Which data are missing for a defensible loss estimate?",
  "Audit the current model result",
];

function LayerToggle({ checked, disabled = false, title, detail, onChange }: { checked: boolean; disabled?: boolean; title: string; detail: string; onChange?: (checked: boolean) => void }) {
  return <label className={`agent-layer-row ${disabled ? "unavailable" : ""}`}>
    <span><strong>{title}</strong><small>{detail}</small></span>
    <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange?.(event.target.checked)} />
  </label>;
}

export function GeoAgentPanel({ onClose, view, scope, hazard, selection, viewport, visibleEventCount, analysisRun, hasDemoRun, layers, onLayersChange, question, onQuestionChange, answer, loading, onSubmit }: Props) {
  const locationLabel = selection?.title ?? (scope === "local" ? "Bethlehem demonstration extent" : "No selected feature");
  const resultLayerCount = Number(layers.analysis && Boolean(analysisRun)) + Number(layers.demo && hasDemoRun);

  return <aside className="ai-drawer geo-agent" aria-label="Map-aware geospatial agent">
    <div className="drawer-head">
      <div><span className="eyebrow">Map-aware workspace</span><h2>Geospatial CAT Agent</h2><p>Ask · visualize · verify</p></div>
      <button className="icon-button" onClick={onClose} aria-label="Close geospatial agent"><X size={18} /></button>
    </div>

    <section className="agent-context" aria-label="Current map context">
      <div className="agent-section-title"><MapPinned size={16} /><span><strong>Current map context</strong><small>Updated from the visible workspace</small></span><i className="context-live" /></div>
      <dl>
        <div><dt>Workspace</dt><dd>{view} · {scope}</dd></div>
        <div><dt>Focus</dt><dd>{locationLabel}</dd></div>
        <div><dt>Viewport</dt><dd className="number-value">{viewport ? `${viewport.center[1].toFixed(3)}, ${viewport.center[0].toFixed(3)} · z${viewport.zoom.toFixed(1)}` : "Loading map…"}</dd></div>
        <div><dt>Visible data</dt><dd>{visibleEventCount} event markers · {resultLayerCount} result layers</dd></div>
        <div><dt>Peril filter</dt><dd>{hazard}</dd></div>
      </dl>
    </section>

    <section className="agent-layers" aria-label="Map layer controls">
      <div className="agent-section-title"><Layers3 size={16} /><span><strong>Layers & appearance</strong><small>Changes apply directly to the map</small></span></div>
      <LayerToggle checked={layers.events} title="Official event markers" detail="GDACS locations; not impact footprints" onChange={(events) => onLayersChange({ ...layers, events })} />
      <LayerToggle checked={layers.analysis} title="Analysis footprint" detail={analysisRun ? "Published hazard geometry from this run" : "Run an analysis to add this layer"} disabled={!analysisRun} onChange={(analysis) => onLayersChange({ ...layers, analysis })} />
      <LayerToggle checked={layers.demo} title="Modelled demo assets" detail={hasDemoRun ? "Labelled sample result" : "Open the guided demo to add this layer"} disabled={!hasDemoRun} onChange={(demo) => onLayersChange({ ...layers, demo })} />
      <label className="agent-slider"><span><Eye size={14} /> Footprint opacity</span><strong className="number-value">{Math.round(layers.analysisOpacity * 100)}%</strong><input type="range" min="10" max="80" step="5" value={Math.round(layers.analysisOpacity * 100)} onChange={(event) => onLayersChange({ ...layers, analysisOpacity: Number(event.target.value) / 100 })} /></label>
      <div className="certainty-law"><ShieldCheck size={14} /><span>Layer colors are fixed by certainty and severity. They are not decorative style controls.</span></div>
    </section>

    <section className="agent-tools" aria-label="Connected tools and activity">
      <div className="agent-section-title"><Activity size={16} /><span><strong>Tools & data activity</strong><small>What the agent can actually use</small></span></div>
      <div className="tool-status connected"><Database size={15} /><span><strong>NHC · USGS · NIFC · FEMA · USACE NSI</strong><small>Connected authoritative and screening services</small></span><CheckCircle2 size={14} /></div>
      <div className="tool-status connected"><Radio size={15} /><span><strong>Map context</strong><small>Viewport, selection, filter and visible results</small></span><CheckCircle2 size={14} /></div>
      <div className="tool-status unavailable"><Database size={15} /><span><strong>Organization PostGIS</strong><small>Connector not configured</small></span><i>OFF</i></div>
      <div className="tool-status unavailable"><Satellite size={15} /><span><strong>Sentinel-2 imagery</strong><small>Connector not configured</small></span><i>OFF</i></div>
      <div className="tool-status unavailable"><Box size={15} /><span><strong>Overture roads · 3D buildings</strong><small>BigQuery/extrusion connector not configured</small></span><i>OFF</i></div>
    </section>

    {answer && <section className="agent-answer" aria-live="polite">
      <span className="eyebrow">Grounded response</span>
      <p>{answer.message}</p>
      {answer.tool_trace.length > 0 && <div className="agent-trace">{answer.tool_trace.map((item) => <div key={item.id}><i className={item.status === "completed" || item.status === "success" ? "done" : ""} /><span><strong>{item.tool}</strong><small>{item.summary}</small></span></div>)}</div>}
      <small>Numbers: {answer.numbers_source === "approved_tools" ? "approved calculation tools" : "no numeric claims"}.</small>
    </section>}

    <form onSubmit={onSubmit} className="agent-composer">
      <label htmlFor="agent-question">Ask about this map</label>
      <textarea id="agent-question" value={question} onChange={(event) => onQuestionChange(event.target.value)} rows={3} placeholder="Analyze the selected area with connected data…" />
      <button className="primary" type="submit" disabled={loading || !question.trim()}><Bot size={16} />{loading ? "Checking approved tools…" : "Run grounded request"}</button>
    </form>
    <div className="prompt-chips">{PROMPTS.map((prompt) => <button type="button" key={prompt} onClick={() => onQuestionChange(prompt)}>{prompt}</button>)}</div>
    <p className="agent-disclaimer">Simulations and demonstrations remain explicitly labelled. The agent cannot activate unconfigured data connectors or invent map results.</p>
  </aside>;
}

export type { LayerState as GeoAgentLayerState };
