"use client";

import { useState } from "react";
import { Download, ExternalLink, Layers3, Play, ShieldCheck } from "lucide-react";
import type { HistoricDataset, HistoricEvent } from "./data";
import { pipelineFor } from "./data";
import { LossCurve } from "./LossCurve";

const HAZARD_SYMBOL: Record<string, string> = { EQ: "✦", TC: "◉", FL: "≈", WF: "▲", TO: "↯" };

function downloadFile(name: string, type: string, body: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click();
  URL.revokeObjectURL(url);
}

function LossLine({ label, loss, event }: { label: string; loss: HistoricEvent["economic_loss"]; event: HistoricEvent }) {
  const sources = loss.source_ids.map((id) => event.sources.find((source) => source.id === id)).filter(Boolean);
  return <article className="historic-loss-line"><span>{label}</span><strong>{loss.display}</strong><small>{loss.currency} · loss year {loss.loss_year} · {loss.inflation_basis}</small>{sources.length > 0 ? sources.map((source) => <details key={source!.id}><summary>{source!.name}</summary><a href={source!.url} target="_blank" rel="noreferrer">Full reference <ExternalLink size={12} /></a></details>) : <em>No qualifying public source value was supplied.</em>}</article>;
}

export function EventCard({ event, selectedDataset }: { event: HistoricEvent; selectedDataset: HistoricDataset }) {
  const [layers, setLayers] = useState(() => new Set([selectedDataset.slug]));
  const [showScript, setShowScript] = useState(false);
  const [curveView, setCurveView] = useState<"cumulative" | "exceedance">("cumulative");
  const toggleLayer = (slug: string) => setLayers((current) => { const next = new Set(current); if (next.has(slug)) next.delete(slug); else next.add(slug); return next; });
  const extract = () => {
    const source = event.sources.find((item) => item.id === selectedDataset.source_id);
    const geojson = { type: "FeatureCollection", name: `${event.slug}-${selectedDataset.slug}`, provenance: selectedDataset.provenance, geometry_status: selectedDataset.geometry_status, features: [{ type: "Feature", properties: { event: event.name, role: "official source/origin marker", source: source?.name, source_url: source?.url }, geometry: { type: "Point", coordinates: event.center } }] };
    const csv = `event,dataset,provenance,resolution,vintage,unit,denominator,geometry_status\n"${event.name}","${selectedDataset.name}","${selectedDataset.provenance}","${selectedDataset.resolution}","${selectedDataset.vintage}","${selectedDataset.unit}","${selectedDataset.denominator}","${selectedDataset.geometry_status}"\n`;
    downloadFile(`${event.slug}-${selectedDataset.slug}.geojson`, "application/geo+json", JSON.stringify(geojson, null, 2));
    downloadFile(`${event.slug}-${selectedDataset.slug}.csv`, "text/csv", csv);
    downloadFile(`${event.slug}-sources.json`, "application/json", JSON.stringify({ event: event.slug, retrieved_for_bundle: new Date().toISOString(), sources: event.sources }, null, 2));
  };

  return <article className="historic-event-card">
    <header className="historic-event-head"><div><span className="eyebrow">Historic event · {selectedDataset.provenance}</span><h1>{event.name}</h1><p>{event.region} · {event.start_date}–{event.end_date}</p></div><a href={event.sources[0].url} target="_blank" rel="noreferrer">Authoritative event page <ExternalLink size={14} /></a></header>
    <section className="historic-map-panel">
      <div className="historic-map" aria-label={`${event.name} footprint map`}><div className="map-grid" /><div className={`historic-origin ${event.hazard_code}`} style={{ left: "50%", top: "48%" }}><b>{HAZARD_SYMBOL[event.hazard_code] ?? "•"}</b><span>Official source/origin<br />{event.center[1].toFixed(4)}, {event.center[0].toFixed(4)}</span></div><div className="geometry-state"><Layers3 size={18} /><strong>{selectedDataset.name}</strong><span>{selectedDataset.geometry_status === "reference_only" ? "Geometry is available only through the cited authoritative dataset; it is not copied or approximated here." : "Impacted-area geometry is not available from the selected source."}</span></div></div>
      <aside className="historic-layer-control"><strong>Layers</strong>{event.datasets.map((dataset) => <label key={dataset.slug}><input type="checkbox" checked={layers.has(dataset.slug)} onChange={() => toggleLayer(dataset.slug)} /><span>{dataset.name}<small>{dataset.provenance} · {event.sources.find((source) => source.id === dataset.source_id)?.name}</small></span></label>)}<div className="historic-legend"><span><i className="origin" /> Source/origin marker · WGS84</span><span><i className="impact" /> Impacted area · {selectedDataset.unit}</span><span><i className="loss" /> Loss overlay · nominal source currency</span></div></aside>
    </section>
    <section className="historic-loss-panel"><h2>Loss panel</h2><p>{event.headline_loss}</p><div><LossLine label="Insured loss" loss={event.insured_loss} event={event} /><LossLine label="Total economic loss" loss={event.economic_loss} event={event} /></div></section>
    <section className="historic-density"><h2>Impact density</h2><div className="density-empty"><ShieldCheck size={20} /><strong>Density plot not available from source extract</strong><span>The selected dataset states its denominator as “{selectedDataset.denominator},” but no redistributable observation array is checked in. No synthetic bins are shown.</span><div className="density-scale"><i /><i /><i /><i /><i /></div><small>Sequential scale: no values · denominator: {selectedDataset.denominator}</small></div></section>
    <section className="historic-curves"><div className="curve-head"><div><h2>Cumulative loss curve</h2><p>Views remain separate and explicitly labelled.</p></div><div><button className={curveView === "cumulative" ? "active" : ""} onClick={() => setCurveView("cumulative")}>Cumulative</button><button className={curveView === "exceedance" ? "active" : ""} onClick={() => setCurveView("exceedance")}>Exceedance probability</button></div></div><LossCurve losses={[]} currency={event.economic_loss.currency} view={curveView} /></section>
    <section className="historic-extract"><button className="primary" type="button" onClick={extract}><Download size={15} /> Download extracted bundle</button><button type="button" onClick={() => setShowScript((value) => !value)}><Play size={14} /> {showScript ? "Hide the script" : "Show the script"}</button>{showScript && <ol>{pipelineFor(event, selectedDataset).map((step) => <li key={step.step}><b>{step.step}</b><div><strong>{step.label}</strong><p>{step.detail}</p><small>Units: {step.units}</small></div></li>)}</ol>}</section>
    <aside className="historic-source-drawer"><h2>Source drawer</h2><p>Every displayed event figure resolves here.</p>{event.sources.map((source) => <article key={source.id}><strong>{source.name}</strong><span>Retrieved {source.retrieved_at} · {source.license}</span><small>Feeds: {source.panels.join(", ")}</small><a href={source.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={12} /></a></article>)}</aside>
  </article>;
}
