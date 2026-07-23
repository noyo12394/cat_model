"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowLeftRight, Check, ExternalLink, Info, Pause, Play, Search, Sparkles } from "lucide-react";
import type { GlobalEvent } from "@/lib/types";
import type { MapSelection } from "../RiskMap";
import { CatastropheGlobe, type GlobeEntry } from "./CatastropheGlobe";
import {
  GENOME_TRAITS,
  HISTORICAL_GENOME_EVENTS,
  ARCHIVE_SOURCES,
  euclideanDistance,
  hazardColor,
  nearestNeighbors,
  outlierDistance,
  similarityPercent,
  traitVector,
  type GenomeHazard,
  type HistoricalGenomeEvent,
} from "./genomeData";

type LabMode = "atlas" | "genome" | "compare" | "catalog" | "archive";
type AtlasSource = "live" | "historical";

type UsgsArchiveFeature = {
  id: string;
  properties: {
    title?: string;
    mag?: number | null;
    place?: string | null;
    time?: number | null;
    updated?: number | null;
    url?: string | null;
  };
  geometry?: { coordinates?: number[] | null } | null;
};

type Props = {
  liveEvents: GlobalEvent[];
  onSelectLive: (selection: MapSelection) => void;
};

const HAZARDS: Array<{ id: "all" | GenomeHazard; label: string }> = [
  { id: "all", label: "All hazards" },
  { id: "earthquake", label: "Earthquake" },
  { id: "cyclone", label: "Cyclone" },
  { id: "flood", label: "Flood" },
  { id: "wildfire", label: "Wildfire" },
  { id: "volcano", label: "Volcano" },
];

function liveHazard(eventType: string): GenomeHazard | null {
  if (/^(eq|earthquake)$/i.test(eventType)) return "earthquake";
  if (/^(tc|cyclone|storm|wind)$/i.test(eventType)) return "cyclone";
  if (/^(fl|flood)$/i.test(eventType)) return "flood";
  if (/^(wf|fire|wildfire)$/i.test(eventType)) return "wildfire";
  if (/^(vo|volcano)$/i.test(eventType)) return "volcano";
  return null;
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="genome-metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function MetadataHelix({
  event,
  contrastWith,
  selectedTraitIndex,
  onSelectTrait,
  isScanning = false,
}: {
  event: HistoricalGenomeEvent;
  contrastWith?: HistoricalGenomeEvent;
  selectedTraitIndex?: number;
  onSelectTrait?: (index: number) => void;
  isScanning?: boolean;
}) {
  const vector = traitVector(event);
  const comparisonVector = contrastWith ? traitVector(contrastWith) : null;
  const width = 640;
  const step = 18;
  const top = 24;
  const height = top * 2 + step * (GENOME_TRAITS.length - 1);
  return <div className={`metadata-helix${isScanning ? " is-scanning" : ""}`} role="group" aria-label={`Metadata signature for ${event.name}; each rung represents one of ${GENOME_TRAITS.length} categorical catalogue traits`}>
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
      <defs>
        <filter id="genome-lab-glow"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      {GENOME_TRAITS.map((trait, index) => {
        const y = top + index * step;
        const spread = 110 + Math.abs(Math.sin(index * 0.68)) * 95;
        const left = width / 2 - spread;
        const right = width / 2 + spread;
        const active = vector[index] === 1;
        const differs = comparisonVector ? comparisonVector[index] !== vector[index] : false;
        const selected = selectedTraitIndex === index;
        const color = active ? hazardColor(event.hazard) : "#38516e";
        return <g
          key={trait.id}
          className={`${active ? "active" : "inactive"}${selected ? " selected" : ""}${onSelectTrait ? " interactive" : ""}`}
          onClick={() => onSelectTrait?.(index)}
          onKeyDown={(keyboardEvent) => {
            if (onSelectTrait && (keyboardEvent.key === "Enter" || keyboardEvent.key === " ")) {
              keyboardEvent.preventDefault();
              onSelectTrait(index);
            }
          }}
          role={onSelectTrait ? "button" : undefined}
          tabIndex={onSelectTrait ? 0 : undefined}
          aria-label={onSelectTrait ? `Trait ${index + 1}: ${trait.label}, ${active ? "present" : "not encoded"}` : undefined}
        >
          <title>{`${String(index + 1).padStart(2, "0")} · ${trait.label}: ${active ? "present" : "not encoded"}`}</title>
          {selected && <rect className="trait-scanner" x="12" y={y - 12} width={width - 24} height="24" rx="4" />}
          <path d={`M ${left} ${y - 8} Q ${width / 2 - 45} ${y} ${right} ${y + 8}`} fill="none" stroke={color} strokeWidth={active ? 3.2 : 1.2} opacity={active ? 0.92 : 0.48} filter={active ? "url(#genome-lab-glow)" : undefined} />
          <circle cx={left} cy={y - 8} r={active ? 5 : 3.5} fill={color} /><circle cx={right} cy={y + 8} r={active ? 5 : 3.5} fill={color} />
          <text x={width / 2} y={y + 3} textAnchor="middle">{String(index + 1).padStart(2, "0")}</text>
          {differs && <rect x={width - 20} y={y - 5} width="8" height="8" rx="1" fill="#FF8A3D" />}
        </g>;
      })}
    </svg>
  </div>;
}

function EventDetails({ event, onExplore }: { event: HistoricalGenomeEvent; onExplore: (event: HistoricalGenomeEvent) => void }) {
  const neighbors = nearestNeighbors(event);
  return <aside className="genome-detail-card">
    <div className="genome-detail-heading"><span className="hazard-dot" style={{ background: hazardColor(event.hazard) }} /><div><span className="eyebrow">Curated historical metadata</span><h2>{event.name}</h2><p>{event.dateLabel} · {event.country}</p></div></div>
    <p>{event.summary}</p>
    <dl className="genome-detail-facts"><div><dt>Hazard class</dt><dd>{titleCase(event.hazard)}</dd></div><div><dt>Onset class</dt><dd>{titleCase(event.onset)}</dd></div><div><dt>Reference point</dt><dd>{event.center[1].toFixed(2)}, {event.center[0].toFixed(2)}</dd></div><div><dt>Catalogue outlier</dt><dd>{outlierDistance(event).toFixed(2)} / vector distance</dd></div></dl>
    <div className="genome-source-link"><span>Archive source</span><a href={event.sourceUrl} target="_blank" rel="noreferrer">{event.sourceLabel}<ExternalLink size={13} /></a></div>
    <p className="genome-coordinate-note"><Info size={13} /> {event.coordinateNote}</p>
    <div className="genome-neighbors"><span>Nearest catalogue neighbours</span>{neighbors.map((neighbor) => <button key={neighbor.event.id} onClick={() => onExplore(neighbor.event)}><span>{neighbor.event.name}</span><strong>{neighbor.similarity}%</strong></button>)}</div>
  </aside>;
}

export function CatastropheGenomeLab({ liveEvents, onSelectLive }: Props) {
  const [mode, setMode] = useState<LabMode>("atlas");
  const [atlasSource, setAtlasSource] = useState<AtlasSource>("live");
  const [historicalHazard, setHistoricalHazard] = useState<"all" | GenomeHazard>("all");
  const [autoRotate, setAutoRotate] = useState(() => typeof window === "undefined" ? false : !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [selectedHistoricalId, setSelectedHistoricalId] = useState(HISTORICAL_GENOME_EVENTS[0].id);
  const [selectedLiveId, setSelectedLiveId] = useState<string | null>(null);
  const [compareLeftId, setCompareLeftId] = useState(HISTORICAL_GENOME_EVENTS[10].id);
  const [compareRightId, setCompareRightId] = useState(HISTORICAL_GENOME_EVENTS[13].id);
  const [catalogSort, setCatalogSort] = useState<"year" | "hazard" | "name">("year");
  const [activeTraitIndex, setActiveTraitIndex] = useState(0);
  const [traitScanPlaying, setTraitScanPlaying] = useState(false);
  const [archiveMinimumMagnitude, setArchiveMinimumMagnitude] = useState("6");
  const [archiveOrder, setArchiveOrder] = useState<"time" | "magnitude">("time");
  const [archiveStatus, setArchiveStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const [archiveResults, setArchiveResults] = useState<UsgsArchiveFeature[]>([]);
  const [archiveUrl, setArchiveUrl] = useState<string | null>(null);

  const selectedHistorical = useMemo(() => HISTORICAL_GENOME_EVENTS.find((event) => event.id === selectedHistoricalId) ?? HISTORICAL_GENOME_EVENTS[0], [selectedHistoricalId]);
  const compareLeft = useMemo(() => HISTORICAL_GENOME_EVENTS.find((event) => event.id === compareLeftId) ?? HISTORICAL_GENOME_EVENTS[0], [compareLeftId]);
  const compareRight = useMemo(() => HISTORICAL_GENOME_EVENTS.find((event) => event.id === compareRightId) ?? HISTORICAL_GENOME_EVENTS[1], [compareRightId]);
  const historicalEvents = useMemo(() => historicalHazard === "all" ? HISTORICAL_GENOME_EVENTS : HISTORICAL_GENOME_EVENTS.filter((event) => event.hazard === historicalHazard), [historicalHazard]);
  const liveEntries = useMemo<GlobeEntry[]>(() => liveEvents.map((event) => {
    const hazard = liveHazard(event.event_type);
    return { id: event.event_id, name: event.name, subtitle: `${event.event_type} · ${event.alert_level} alert`, center: event.center, color: hazard ? hazardColor(hazard) : "#8FA3B8", height: event.alert_level === "red" ? 0.25 : event.alert_level === "orange" ? 0.18 : 0.12, detail: `${event.source} · updated ${event.modified_at}` };
  }), [liveEvents]);
  const historicalEntries = useMemo<GlobeEntry[]>(() => historicalEvents.map((event) => ({ id: event.id, name: event.name, subtitle: `${event.dateLabel} · ${titleCase(event.hazard)}`, center: event.center, color: hazardColor(event.hazard), height: 0.16, detail: event.coordinateNote })), [historicalEvents]);
  const catalogEvents = useMemo(() => [...historicalEvents].sort((a, b) => catalogSort === "year" ? b.year - a.year : catalogSort === "hazard" ? a.hazard.localeCompare(b.hazard) || b.year - a.year : a.name.localeCompare(b.name)), [catalogSort, historicalEvents]);
  const activeEntries = atlasSource === "live" ? liveEntries : historicalEntries;

  useEffect(() => {
    if (!traitScanPlaying) return;
    const timer = window.setInterval(() => {
      setActiveTraitIndex((index) => (index + 1) % GENOME_TRAITS.length);
    }, 780);
    return () => window.clearInterval(timer);
  }, [traitScanPlaying]);

  function openHistorical(event: HistoricalGenomeEvent, next: LabMode = "genome") {
    setSelectedHistoricalId(event.id);
    setMode(next);
  }

  function selectGlobeEntry(entry: GlobeEntry) {
    if (atlasSource === "historical") {
      const event = HISTORICAL_GENOME_EVENTS.find((candidate) => candidate.id === entry.id);
      if (event) openHistorical(event);
      return;
    }
    const event = liveEvents.find((candidate) => candidate.event_id === entry.id);
    if (!event) return;
    setSelectedLiveId(event.event_id);
    onSelectLive({ id: event.event_id, title: event.name, subtitle: `${event.event_type} · ${event.country}`, status: "Officially reported", source: event.source, center: event.center, zoom: 7 });
  }

  async function searchUsgsArchive() {
    const minimumMagnitude = Number(archiveMinimumMagnitude);
    if (!Number.isFinite(minimumMagnitude) || minimumMagnitude < 0 || minimumMagnitude > 10) {
      setArchiveStatus("error");
      setArchiveError("Choose a magnitude between 0 and 10.");
      return;
    }
    const params = new URLSearchParams({
      format: "geojson",
      starttime: "1900-01-01",
      minmagnitude: String(minimumMagnitude),
      limit: "50",
      orderby: archiveOrder === "time" ? "time" : "magnitude",
    });
    const url = `https://earthquake.usgs.gov/fdsnws/event/1/query?${params.toString()}`;
    setArchiveStatus("loading");
    setArchiveError(null);
    setArchiveUrl(url);
    try {
      const response = await fetch(url, { headers: { Accept: "application/geo+json, application/json" } });
      if (!response.ok) throw new Error(`USGS returned ${response.status}`);
      const payload = await response.json() as { features?: UsgsArchiveFeature[] };
      setArchiveResults(Array.isArray(payload.features) ? payload.features : []);
      setArchiveStatus("success");
    } catch (error) {
      setArchiveStatus("error");
      setArchiveError(error instanceof Error ? error.message : "The USGS catalogue could not be reached from this browser.");
      setArchiveResults([]);
    }
  }

  const similarPercent = similarityPercent(compareLeft, compareRight);
  const vectorDistance = euclideanDistance(compareLeft, compareRight);
  const differingTraits = GENOME_TRAITS.filter((_, index) => traitVector(compareLeft)[index] !== traitVector(compareRight)[index]);

  return <section className="genome-lab" aria-label="Catastrophe Genome Lab">
    <header className="genome-lab-header">
      <div><span className="eyebrow">Experimental data-navigation studio</span><h1>Catastrophe Genome Lab</h1><p>Orbit live official event centres or a source-linked historical catalogue, then compare transparent metadata signatures. Country outlines provide geographic context only.</p></div>
      <div className="genome-lab-status"><span><i /> No loss engine connected</span><span>{HISTORICAL_GENOME_EVENTS.length} reference cases</span><span>{ARCHIVE_SOURCES.length} archive sources</span></div>
    </header>
    <div className="genome-mode-tabs" role="tablist" aria-label="Genome Lab modes">
      {(["atlas", "genome", "compare", "catalog", "archive"] as LabMode[]).map((item) => <button key={item} type="button" role="tab" aria-selected={mode === item} className={mode === item ? "active" : ""} onClick={() => setMode(item)}>{item === "atlas" ? "3D atlas" : item === "genome" ? "Trait scan" : item === "compare" ? "Compare" : item === "catalog" ? `Reference set (${HISTORICAL_GENOME_EVENTS.length})` : "Archive sources"}</button>)}
    </div>

    {mode === "atlas" && <div className="genome-atlas-layout">
      <div className="genome-atlas-main">
        <div className="genome-atlas-toolbar"><div className="segmented-control" role="group" aria-label="Atlas data source"><button className={atlasSource === "live" ? "active" : ""} onClick={() => setAtlasSource("live")}>Live GDACS ({liveEntries.length})</button><button className={atlasSource === "historical" ? "active" : ""} onClick={() => setAtlasSource("historical")}>Curated {HISTORICAL_GENOME_EVENTS.length}</button></div>{atlasSource === "historical" && <select aria-label="Filter historical events by hazard" value={historicalHazard} onChange={(event) => setHistoricalHazard(event.target.value as "all" | GenomeHazard)}>{HAZARDS.map((hazard) => <option key={hazard.id} value={hazard.id}>{hazard.label}</option>)}</select>}<button className="orbit-toggle" onClick={() => setAutoRotate((value) => !value)} aria-pressed={autoRotate}>{autoRotate ? <Pause size={14} /> : <Play size={14} />}{autoRotate ? "Pause orbit" : "Orbit globe"}</button></div>
        {activeEntries.length > 0 ? <CatastropheGlobe entries={activeEntries} selectedId={atlasSource === "live" ? selectedLiveId : selectedHistoricalId} onSelect={selectGlobeEntry} autoRotate={autoRotate} /> : <div className="genome-empty">No eligible official-event centres are available in the current live filter. Refresh the Live tab and try again.</div>}
      </div>
      <div className="genome-atlas-side">
        {atlasSource === "historical" ? <EventDetails event={selectedHistorical} onExplore={openHistorical} /> : <div className="live-atlas-card"><span className="eyebrow">Live official metadata</span><h2>{selectedLiveId ? liveEntries.find((entry) => entry.id === selectedLiveId)?.name ?? "Selected event" : "Select a live beacon"}</h2><p>Live beacons use the same GDACS records already visible in the Live workspace. Selecting a beacon opens the normal official-event detail card and never creates an impact surface.</p><div className="live-atlas-key"><span><i style={{ background: hazardColor("earthquake") }} /> Earthquake</span><span><i style={{ background: hazardColor("cyclone") }} /> Cyclone</span><span><i style={{ background: hazardColor("flood") }} /> Flood</span><span><i style={{ background: hazardColor("wildfire") }} /> Wildfire</span></div><p className="genome-coordinate-note"><Info size={13} /> A beacon is the reported event centre, not a hazard footprint, modelled loss, or confidence score.</p></div>}
      </div>
    </div>}

    {mode === "genome" && <div className="genome-helix-layout">
      <aside className="genome-picker"><label>Historical event<select value={selectedHistoricalId} onChange={(event) => setSelectedHistoricalId(event.target.value)}>{HISTORICAL_GENOME_EVENTS.map((event) => <option key={event.id} value={event.id}>{event.dateLabel} · {event.name}</option>)}</select></label><EventDetails event={selectedHistorical} onExplore={openHistorical} /></aside>
      <div className="helix-panel"><div className="helix-panel-head"><div><span className="eyebrow">{GENOME_TRAITS.length} categorical metadata loci</span><h2>{selectedHistorical.name}</h2></div><span className="helix-count">{traitVector(selectedHistorical).filter(Boolean).length} active</span></div><div className="trait-scan-controls"><div><span className="eyebrow">Selected locus {String(activeTraitIndex + 1).padStart(2, "0")}</span><strong>{GENOME_TRAITS[activeTraitIndex].label}</strong><small>{traitVector(selectedHistorical)[activeTraitIndex] ? "Encoded for this reference case" : "Not encoded for this reference case"} · {GENOME_TRAITS[activeTraitIndex].group}</small></div><button type="button" onClick={() => setTraitScanPlaying((playing) => !playing)} aria-pressed={traitScanPlaying}>{traitScanPlaying ? <Pause size={14} /> : <Play size={14} />}{traitScanPlaying ? "Pause scan" : "Play trait scan"}</button></div><MetadataHelix event={selectedHistorical} selectedTraitIndex={activeTraitIndex} onSelectTrait={(index) => { setActiveTraitIndex(index); setTraitScanPlaying(false); }} isScanning={traitScanPlaying} /><div className="trait-matrix">{GENOME_TRAITS.map((trait, index) => <button type="button" key={trait.id} className={`${traitVector(selectedHistorical)[index] ? "active" : ""}${activeTraitIndex === index ? " selected" : ""}`} onClick={() => { setActiveTraitIndex(index); setTraitScanPlaying(false); }}><span>{String(index + 1).padStart(2, "0")}</span><strong>{trait.label}</strong><small>{traitVector(selectedHistorical)[index] ? "present" : "not encoded"}</small></button>)}</div><p className="genome-method"><Info size={14} /> Click a rung or trait card to inspect it. “Play trait scan” is a bounded interface animation, not event evolution. This visual is metadata navigation only—not genetic data, a physical event model, a fragility curve, or a forecast.</p></div>
    </div>}

    {mode === "compare" && <div className="genome-compare-layout">
      <div className="compare-selects"><label>Reference event<select value={compareLeftId} onChange={(event) => setCompareLeftId(event.target.value)}>{HISTORICAL_GENOME_EVENTS.map((event) => <option key={event.id} value={event.id}>{event.dateLabel} · {event.name}</option>)}</select></label><ArrowLeftRight size={20} /><label>Comparison event<select value={compareRightId} onChange={(event) => setCompareRightId(event.target.value)}>{HISTORICAL_GENOME_EVENTS.map((event) => <option key={event.id} value={event.id}>{event.dateLabel} · {event.name}</option>)}</select></label></div>
      <div className="compare-metrics"><Metric label="Metadata resemblance" value={`${similarPercent}%`} detail={`normalized ${GENOME_TRAITS.length}-trait distance`} /><Metric label="Euclidean distance" value={vectorDistance.toFixed(2)} detail="0 would mean identical encoded traits" /><Metric label="Different loci" value={`${differingTraits.length} / ${GENOME_TRAITS.length}`} detail="categorical differences only" /></div>
      <div className="compare-helices"><article><span className="hazard-dot" style={{ background: hazardColor(compareLeft.hazard) }} /><h2>{compareLeft.name}</h2><MetadataHelix event={compareLeft} contrastWith={compareRight} selectedTraitIndex={activeTraitIndex} /></article><article><span className="hazard-dot" style={{ background: hazardColor(compareRight.hazard) }} /><h2>{compareRight.name}</h2><MetadataHelix event={compareRight} contrastWith={compareLeft} selectedTraitIndex={activeTraitIndex} /></article></div>
      <section className="trait-diff"><h2>Encoded differences</h2>{differingTraits.length ? differingTraits.map((trait, index) => <div key={trait.id}><span>{String(index + 1).padStart(2, "0")}</span><strong>{trait.label}</strong><span>{traitVector(compareLeft)[GENOME_TRAITS.indexOf(trait)] ? compareLeft.name : "Not encoded"}</span><span>{traitVector(compareRight)[GENOME_TRAITS.indexOf(trait)] ? compareRight.name : "Not encoded"}</span></div>) : <p>Both records have identical encoded categorical traits.</p>}</section>
      <p className="genome-method"><Info size={14} /> Resemblance is a transparent catalogue-navigation measure. It is not similarity of loss, severity, likelihood, vulnerability, or human impact.</p>
    </div>}

    {mode === "catalog" && <div className="genome-catalog-layout"><div className="catalog-reference-note"><span className="eyebrow">Curated teaching and comparison set</span><p>These {HISTORICAL_GENOME_EVENTS.length} cases are deliberately selected reference records—not a complete catastrophe archive. Use “Archive sources” for official catalogues and live searches.</p></div><div className="catalog-controls"><div className="segmented-control">{HAZARDS.map((hazard) => <button key={hazard.id} className={historicalHazard === hazard.id ? "active" : ""} onClick={() => setHistoricalHazard(hazard.id)}>{hazard.label}</button>)}</div><label>Sort<select value={catalogSort} onChange={(event) => setCatalogSort(event.target.value as "year" | "hazard" | "name")}><option value="year">Newest first</option><option value="hazard">Hazard class</option><option value="name">Name</option></select></label></div><div className="genome-catalog-table"><div className="catalog-heading"><span>Event</span><span>Class</span><span>Encoded context</span><span>Archive</span></div>{catalogEvents.map((event) => <article key={event.id}><button onClick={() => openHistorical(event)}><i style={{ background: hazardColor(event.hazard) }} /><span><strong>{event.name}</strong><small>{event.dateLabel} · {event.country}</small></span></button><span>{titleCase(event.hazard)}</span><span>{titleCase(event.setting)} · {titleCase(event.onset)}</span><a href={event.sourceUrl} target="_blank" rel="noreferrer">Source <ExternalLink size={13} /></a></article>)}</div><p className="genome-method"><Check size={14} /> All {HISTORICAL_GENOME_EVENTS.length} entries are curated, source-linked metadata records. Their centre points are atlas references—not hazard footprints, loss boundaries, or inferred historical impacts.</p></div>}

    {mode === "archive" && <div className="genome-archive-layout"><section className="archive-intro"><span className="eyebrow">Federated historical archive</span><h2>Search the source; do not imply a single, complete global record.</h2><p>Earthquakes, cyclones, floods, wildfires, volcanoes, and impacts are maintained by different authoritative organizations with different time coverage, licences, and spatial meaning. RiskChain currently queries the USGS earthquake catalogue in-browser and links to the other official archives below.</p></section><section className="archive-source-grid">{ARCHIVE_SOURCES.map((source) => <article key={source.id} className={source.integration === "search" ? "connected" : "external"}><div><span className="archive-status">{source.integration === "search" ? "Search connected" : "Official external archive"}</span><h3>{source.name}</h3><p>{source.provider} · {source.hazardScope}</p></div><dl><div><dt>Coverage</dt><dd>{source.coverage}</dd></div><div><dt>Access</dt><dd>{source.access}</dd></div><div><dt>Refresh</dt><dd>{source.updateCadence}</dd></div></dl><p className="archive-limit"><Info size={13} /> {source.limitation}</p><a href={source.url} target="_blank" rel="noreferrer">Open official archive <ExternalLink size={13} /></a></article>)}</section><section className="usgs-archive-search"><div className="usgs-search-head"><div><span className="eyebrow">Live source query</span><h2>USGS historical earthquake catalogue</h2><p>Returns the first 50 real source records matching the selected threshold, ordered by time or magnitude. The source API supports paging for larger research workflows.</p></div><a href="https://earthquake.usgs.gov/fdsnws/event/1/" target="_blank" rel="noreferrer">API documentation <ExternalLink size={13} /></a></div><div className="usgs-search-controls"><label>Minimum magnitude<input type="number" min="0" max="10" step="0.1" value={archiveMinimumMagnitude} onChange={(event) => setArchiveMinimumMagnitude(event.target.value)} /></label><label>Order<select value={archiveOrder} onChange={(event) => setArchiveOrder(event.target.value as "time" | "magnitude")}><option value="time">Newest first</option><option value="magnitude">Largest first</option></select></label><button type="button" onClick={searchUsgsArchive} disabled={archiveStatus === "loading"}>{archiveStatus === "loading" ? "Querying USGS…" : <><Search size={14} /> Search USGS archive</>}</button></div>{archiveStatus === "error" && <div className="archive-query-state error">The query did not return a usable source response: {archiveError}. <a href="https://earthquake.usgs.gov/fdsnws/event/1/" target="_blank" rel="noreferrer">Open the official catalogue</a>.</div>}{archiveStatus === "success" && <><div className="archive-query-state success">USGS returned {archiveResults.length} source records for this bounded preview. <a href={archiveUrl ?? undefined} target="_blank" rel="noreferrer">Open this exact source query <ExternalLink size={12} /></a></div><div className="archive-result-table"><div><span>Event</span><span>Magnitude</span><span>Depth</span><span>UTC time</span></div>{archiveResults.map((record) => { const coordinates = record.geometry?.coordinates ?? []; const depth = coordinates.length > 2 && Number.isFinite(coordinates[2]) ? `${Number(coordinates[2]).toFixed(1)} km` : "Not reported"; const time = record.properties.time ? new Date(record.properties.time).toISOString().replace("T", " ").replace(".000Z", " UTC") : "Not reported"; return <article key={record.id}><a href={record.properties.url ?? "https://earthquake.usgs.gov/fdsnws/event/1/"} target="_blank" rel="noreferrer"><strong>{record.properties.title ?? record.properties.place ?? record.id}</strong><small>{record.properties.place ?? "Location not reported"}</small></a><span>{record.properties.mag ?? "Not reported"}</span><span>{depth}</span><time>{time}</time></article>; })}</div></>}</section><p className="genome-method"><Info size={14} /> The archive preview is evidence navigation—not a hazard footprint, fragility curve, impact assessment, or loss calculation. Other source families need separate governed ingestion before they can appear as normalized RiskChain records.</p></div>}

    <footer className="genome-lab-footer"><Sparkles size={15} /><span>Future extension path: approved footprints, exposure snapshots, and model-run manifests can be linked only when source licences, resolution, and governance allow it.</span><a href="https://github.com/noyo12394/cat_model/blob/claude/earthpulse-platform-design-00pe94/docs/CATASTROPHE_GENOME.md" target="_blank" rel="noreferrer">Read methodology</a></footer>
  </section>;
}
