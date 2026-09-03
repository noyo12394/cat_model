"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import { BookOpen, Download, ExternalLink, Layers3, MapPinned, PackageOpen, Play, ShieldCheck } from "lucide-react";
import type { HistoricAction, HistoricDataset, HistoricEvent } from "./data";
import { pipelineFor } from "./data";
import { LossCurve } from "./LossCurve";
import styles from "./HistoricExplorer.module.css";
import { historicBasemapStyle, installMissingStyleImageFallback } from "@/lib/mapStyle";

const HAZARD_SYMBOL: Record<string, string> = { EQ: "✦", TC: "◉", FL: "≈", WF: "▲", TO: "↯" };
const HAZARD_COLOR: Record<string, string> = { EQ: "#b48cff", TC: "#4fa8ff", FL: "#49c5dd", WF: "#ff7a45", TO: "#f6a94a" };
const encoder = new TextEncoder();

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function concatBytes(parts: Uint8Array[]) {
  const size = parts.reduce((total, part) => total + part.length, 0);
  const output = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) { output.set(part, offset); offset += part.length; }
  return output;
}

function storedZip(files: Array<{ name: string; content: string }>) {
  const localEntries: Uint8Array[] = [];
  const centralEntries: Uint8Array[] = [];
  let localOffset = 0;

  for (const file of files) {
    const name = encoder.encode(file.name);
    const content = encoder.encode(file.content);
    const crc = crc32(content);
    const local = new Uint8Array(30 + name.length + content.length);
    const localView = new DataView(local.buffer);
    localView.setUint32(0, 0x04034b50, true);
    localView.setUint16(4, 20, true);
    localView.setUint16(6, 0, true);
    localView.setUint16(8, 0, true);
    localView.setUint16(10, 0, true);
    localView.setUint16(12, 0, true);
    localView.setUint32(14, crc, true);
    localView.setUint32(18, content.length, true);
    localView.setUint32(22, content.length, true);
    localView.setUint16(26, name.length, true);
    localView.setUint16(28, 0, true);
    local.set(name, 30);
    local.set(content, 30 + name.length);
    localEntries.push(local);

    const central = new Uint8Array(46 + name.length);
    const centralView = new DataView(central.buffer);
    centralView.setUint32(0, 0x02014b50, true);
    centralView.setUint16(4, 20, true);
    centralView.setUint16(6, 20, true);
    centralView.setUint16(8, 0, true);
    centralView.setUint16(10, 0, true);
    centralView.setUint16(12, 0, true);
    centralView.setUint16(14, 0, true);
    centralView.setUint32(16, crc, true);
    centralView.setUint32(20, content.length, true);
    centralView.setUint32(24, content.length, true);
    centralView.setUint16(28, name.length, true);
    centralView.setUint16(30, 0, true);
    centralView.setUint16(32, 0, true);
    centralView.setUint16(34, 0, true);
    centralView.setUint16(36, 0, true);
    centralView.setUint32(38, 0, true);
    centralView.setUint32(42, localOffset, true);
    central.set(name, 46);
    centralEntries.push(central);
    localOffset += local.length;
  }

  const centralSize = centralEntries.reduce((total, entry) => total + entry.length, 0);
  const end = new Uint8Array(22);
  const endView = new DataView(end.buffer);
  endView.setUint32(0, 0x06054b50, true);
  endView.setUint16(4, 0, true);
  endView.setUint16(6, 0, true);
  endView.setUint16(8, files.length, true);
  endView.setUint16(10, files.length, true);
  endView.setUint32(12, centralSize, true);
  endView.setUint32(16, localOffset, true);
  endView.setUint16(20, 0, true);
  return concatBytes([...localEntries, ...centralEntries, end]);
}

function csvCell(value: string | number) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function evidenceBundle(event: HistoricEvent, dataset: HistoricDataset) {
  const source = event.sources.find((item) => item.id === dataset.source_id);
  const pointSource = event.sources.find((item) => item.id === event.center_source_id);
  const sourcePoint = {
    type: "FeatureCollection",
    name: `${event.slug}-official-reference-point`,
    provenance: "officially reported",
    dataset_geometry_status: dataset.geometry_status,
    features: [{
      type: "Feature",
      properties: {
        event: event.name,
        role: "cited event reference point; not a footprint",
        label: event.center_label,
        source: pointSource?.name,
        source_url: pointSource?.url,
      },
      geometry: { type: "Point", coordinates: event.center },
    }],
  };
  const headers = ["event", "dataset", "provenance", "resolution", "vintage", "unit", "denominator", "geometry_status", "authoritative_source_url"];
  const values = [event.name, dataset.name, dataset.provenance, dataset.resolution, dataset.vintage, dataset.unit, dataset.denominator, dataset.geometry_status, source?.url ?? "not available"];
  const metadataCsv = `${headers.map(csvCell).join(",")}\n${values.map(csvCell).join(",")}\n`;
  const manifest = {
    event: event.slug,
    dataset: dataset.slug,
    geometry_status: dataset.geometry_status,
    authoritative_dataset: source ? { id: source.id, name: source.name, url: source.url, retrieved_at: source.retrieved_at } : null,
    footprint_geometry_reference: event.footprint_geometry_reference,
    sources: event.sources,
    related_reading: event.related_reading,
  };
  const readme = [
    `EarthPulse historic evidence bundle: ${event.name} / ${dataset.name}`,
    "",
    `Dataset geometry status: ${dataset.geometry_status.replaceAll("_", " ")}.`,
    "This bundle does not copy, interpolate, or approximate an authoritative footprint that is not checked into EarthPulse.",
    "event-reference-point.geojson contains only the cited source/origin point and is not the selected footprint.",
    `Open the authoritative dataset: ${source?.url ?? "not available from manifest"}`,
    "See sources.json for source names, URLs, retrieval dates, license notes, and panel attribution.",
  ].join("\n");
  const zip = storedZip([
    { name: "README.txt", content: readme },
    { name: "event-reference-point.geojson", content: JSON.stringify(sourcePoint, null, 2) },
    { name: "dataset-metadata.csv", content: metadataCsv },
    { name: "sources.json", content: JSON.stringify(manifest, null, 2) },
    { name: "pipeline.json", content: JSON.stringify(pipelineFor(event, dataset), null, 2) },
  ]);
  return { name: `${event.slug}-${dataset.slug}-evidence.zip`, blob: new Blob([zip], { type: "application/zip" }) };
}

function HistoricMap({ event, dataset, showReference, showDataset }: { event: HistoricEvent; dataset: HistoricDataset; showReference: boolean; showDataset: boolean }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    let map: import("maplibre-gl").Map | undefined;
    const host = ref.current;
    const start = async () => {
      if (!host) return;
      const maplibre = (await import("maplibre-gl")).default;
      if (!alive) return;
      map = new maplibre.Map({
        container: host,
        style: historicBasemapStyle,
        center: event.center,
        zoom: event.map_zoom,
        attributionControl: { compact: true },
      });
      installMissingStyleImageFallback(map);
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
      map.on("load", () => {
        if (!map || !showReference) return;
        map.addSource("historic-reference-point", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "Point", coordinates: event.center } } });
        map.addLayer({ id: "historic-reference-halo", type: "circle", source: "historic-reference-point", paint: { "circle-radius": 19, "circle-color": HAZARD_COLOR[event.hazard_code] ?? "#4fa8ff", "circle-opacity": .18, "circle-blur": .3 } });
        map.addLayer({ id: "historic-reference-point", type: "circle", source: "historic-reference-point", paint: { "circle-radius": 7, "circle-color": HAZARD_COLOR[event.hazard_code] ?? "#4fa8ff", "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      });
    };
    void start();
    return () => { alive = false; map?.remove(); host?.replaceChildren(); };
  }, [event, showReference]);

  return <div className="historic-map" aria-label={`${event.name} source map`}>
    <div ref={ref} className={styles.mapCanvas} role="application" aria-label={`Interactive map centered on ${event.center_label}`} />
    <div className="geometry-state"><Layers3 size={18} /><strong>{showDataset ? dataset.name : "Selected dataset layer hidden"}</strong><span>{showDataset ? dataset.geometry_status === "reference_only" ? "The authoritative geometry is linked but not copied or approximated. The map shows only the cited reference point." : "Impacted-area geometry is not available from the selected source. The map shows only the cited reference point." : "Use the layer control to show this dataset's documented availability."}</span></div>
  </div>;
}

function LossLine({ label, loss, event }: { label: string; loss: HistoricEvent["economic_loss"]; event: HistoricEvent }) {
  const sources = loss.source_ids.map((id) => event.sources.find((source) => source.id === id)).filter(Boolean);
  return <article className="historic-loss-line"><span>{label}</span><strong>{loss.display}</strong><small>{loss.currency} · loss year {loss.loss_year} · {loss.inflation_basis}</small>{sources.length > 0 ? sources.map((source) => <details key={source!.id}><summary>{source!.name}</summary><a href={source!.url} target="_blank" rel="noreferrer">Full reference <ExternalLink size={12} /></a></details>) : <em>No qualifying public source value was supplied.</em>}</article>;
}

function ScriptPanel({ event, dataset }: { event: HistoricEvent; dataset: HistoricDataset }) {
  return <ol>{pipelineFor(event, dataset).map((step) => <li key={step.step}><b>{step.step}</b><div><strong>{step.label}</strong><p>{step.detail}</p><small>Units: {step.units}</small></div></li>)}</ol>;
}

function SourceDrawer({ event }: { event: HistoricEvent }) {
  return <aside className="historic-source-drawer"><h2>Source drawer</h2><p>Every displayed event figure resolves here.</p>{event.sources.map((source) => <article key={source.id}><strong>{source.name}</strong><span>Retrieved {source.retrieved_at} · {source.license}</span><small>Feeds: {source.panels.join(", ")}</small><a href={source.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={12} /></a></article>)}</aside>;
}

export function EventCard({ event, selectedDataset, action }: { event: HistoricEvent; selectedDataset: HistoricDataset; action: HistoricAction }) {
  const [showReference, setShowReference] = useState(true);
  const [showDataset, setShowDataset] = useState(true);
  const [showScript, setShowScript] = useState(false);
  const [curveView, setCurveView] = useState<"cumulative" | "exceedance">("cumulative");
  const selectedSource = event.sources.find((source) => source.id === selectedDataset.source_id);
  const prepareDownload = (click: ReactMouseEvent<HTMLAnchorElement>) => {
    const bundle = evidenceBundle(event, selectedDataset);
    const url = URL.createObjectURL(bundle.blob);
    click.currentTarget.href = url;
    click.currentTarget.download = bundle.name;
    window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
  };
  const header = <header className="historic-event-head"><div><span className="eyebrow">Historic event · {selectedDataset.provenance}</span><h1>{event.name}</h1><p>{event.region} · {event.start_date}–{event.end_date}</p></div><div className={styles.headerLinks}>{selectedSource && <a href={selectedSource.url} target="_blank" rel="noreferrer">Authoritative dataset <ExternalLink size={14} /></a>}{event.slug === "camp-fire-2018" && <Link href="/fire">Continue in FIRE Lab →</Link>}</div></header>;

  if (action === "download") return <article className="historic-event-card">
    {header}
    <section className={`historic-extract ${styles.actionPanel}`}>
      <PackageOpen size={24} />
      <h2>Download the evidence bundle</h2>
      <p>One ZIP contains a cited reference-point GeoJSON, dataset metadata CSV, sources.json, pipeline.json, and a README that states exactly what is and is not included.</p>
      <div className={styles.availability}><strong>Dataset availability:</strong> {selectedDataset.geometry_status.replaceAll("_", " ")}. The authoritative footprint is never replaced with generated geometry.</div>
      <div className={styles.actionButtons}><a href="#download" download={`${event.slug}-${selectedDataset.slug}-evidence.zip`} className={styles.primaryAction} onClick={prepareDownload}><Download size={15} /> Download ZIP bundle</a>{selectedSource && <a href={selectedSource.url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Open official data source</a>}<button type="button" onClick={() => setShowScript((value) => !value)}><Play size={14} /> {showScript ? "Hide the script" : "Show the script"}</button></div>
      {showScript && <ScriptPanel event={event} dataset={selectedDataset} />}
    </section>
    <SourceDrawer event={event} />
  </article>;

  if (action === "read") return <article className="historic-event-card">
    {header}
    <section className={`historic-extract ${styles.actionPanel}`}>
      <BookOpen size={24} />
      <h2>Read authoritative event material</h2>
      <p>These links go directly to the agencies that publish the event record and selected dataset. EarthPulse does not substitute generated summaries for the source material.</p>
      <div className={styles.readingList}>{event.related_reading.map((reading) => { const source = event.sources.find((item) => item.id === reading.source_id); return <a key={reading.url} href={reading.url} target="_blank" rel="noreferrer"><span className={styles.sourceLink}>{reading.title} <ExternalLink size={13} /></span><small>{source?.name} · retrieved {source?.retrieved_at}</small></a>; })}</div>
    </section>
    <SourceDrawer event={event} />
  </article>;

  return <article className="historic-event-card">
    {header}
    <section className="historic-map-panel">
      <HistoricMap event={event} dataset={selectedDataset} showReference={showReference} showDataset={showDataset} />
      <aside className="historic-layer-control"><strong>Layers</strong><label><input type="checkbox" checked={showReference} onChange={() => setShowReference((value) => !value)} /><span>Source/origin point<small>officially reported · {event.sources.find((source) => source.id === event.center_source_id)?.name}</small></span></label><label><input type="checkbox" checked={showDataset} onChange={() => setShowDataset((value) => !value)} /><span>{selectedDataset.name}<small>{selectedDataset.provenance} · {selectedSource?.name}</small></span></label><label><input type="checkbox" checked={false} disabled readOnly /><span>Loss overlay<small>not available from source · no county/ZIP loss array checked in</small></span></label><div className="historic-legend"><span><i className="origin" /> {HAZARD_SYMBOL[event.hazard_code] ?? "•"} source point · WGS84 degrees</span><span><i className="impact" /> Selected data · {selectedDataset.unit}</span><span><i className="loss" /> Loss overlay · not available</span></div></aside>
    </section>
    <section className="historic-loss-panel"><h2>Loss panel</h2><p>{event.headline_loss}</p><div><LossLine label="Insured loss" loss={event.insured_loss} event={event} /><LossLine label="Total economic loss" loss={event.economic_loss} event={event} /></div></section>
    <section className="historic-density"><h2>Impact density</h2><div className="density-empty"><ShieldCheck size={20} /><strong>Density plot not available from source extract</strong><span>The selected dataset states its denominator as “{selectedDataset.denominator},” but no redistributable observation array is checked in. No synthetic bins are shown.</span><div className="density-scale"><i /><i /><i /><i /><i /></div><small>Sequential scale: no values · denominator: {selectedDataset.denominator} · units: {selectedDataset.unit}</small></div></section>
    <section className="historic-curves"><div className="curve-head"><div><h2>Cumulative loss curve</h2><p>Views remain separate and explicitly labelled.</p></div><div><button className={curveView === "cumulative" ? "active" : ""} onClick={() => setCurveView("cumulative")}>Cumulative</button><button className={curveView === "exceedance" ? "active" : ""} onClick={() => setCurveView("exceedance")}>Exceedance probability</button></div></div><LossCurve losses={[]} currency={event.economic_loss.currency} view={curveView} observationUnit={selectedDataset.denominator} /></section>
    <section className="historic-extract"><a className="primary" href="#download" download={`${event.slug}-${selectedDataset.slug}-evidence.zip`} onClick={prepareDownload}><MapPinned size={15} /> One-tap extract (.zip)</a>{selectedSource && <a href={selectedSource.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={13} /></a>}<button type="button" onClick={() => setShowScript((value) => !value)}><Play size={14} /> {showScript ? "Hide the script" : "Show the script"}</button>{showScript && <ScriptPanel event={event} dataset={selectedDataset} />}</section>
    <SourceDrawer event={event} />
  </article>;
}
