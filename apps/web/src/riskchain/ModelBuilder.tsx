"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CalendarDays, CheckCircle2, Database, FlaskConical, Play, Radio, RefreshCw, Search } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AnalysisHazard, AnalysisLocation, AnalysisMode, AnalysisRunResult, HazardEventSearchResponse } from "@/lib/types";

type RunnableMode = Exclude<AnalysisMode, "demo">;
type Props = {
  location: AnalysisLocation | null;
  onRequestLocation: () => void;
  onDemo: () => Promise<void>;
  onResult: (result: AnalysisRunResult) => void;
  onNotice: (message: string) => void;
};

const MODES: Array<{ id: RunnableMode; label: string; detail: string }> = [
  { id: "live", label: "Live event", detail: "NWS · NHC · USGS · NIFC" },
  { id: "historical", label: "Historical", detail: "USGS + linked archives" },
  { id: "hypothetical", label: "Return period", detail: "FEMA NFHL (flood)" },
];

const HAZARD_LABELS: Record<AnalysisHazard, string> = {
  hurricane: "Tropical cyclone",
  earthquake: "Earthquake",
  flood: "Flood",
  wildfire: "Wildfire",
};

type HazardCapability = {
  id: AnalysisHazard;
  state: "connected" | "archive_only" | "not_connected";
  source: string;
  sourceUrl: string;
  detail: string;
};

// Show the full multi-hazard product scope, but distinguish a connected,
// executable source from an external archive or a model that has not yet been
// connected. Hiding those choices made the interface look single-hazard; making
// them runnable would be worse because it would fabricate an analysis path.
const HAZARD_CAPABILITIES: Record<RunnableMode, HazardCapability[]> = {
  live: [
    { id: "earthquake", state: "connected", source: "USGS ShakeMap", sourceUrl: "https://earthquake.usgs.gov/data/shakemap/", detail: "Published shaking contours are screened when a ShakeMap is available." },
    { id: "flood", state: "connected", source: "NWS active alerts", sourceUrl: "https://www.weather.gov/documentation/services-web-api", detail: "Published NWS flood-alert polygons support exposure screening, not inundation or loss modelling." },
    { id: "wildfire", state: "connected", source: "NIFC WFIGS", sourceUrl: "https://data-nifc.opendata.arcgis.com/", detail: "Mapped current incident perimeters support exposure screening only." },
    { id: "hurricane", state: "connected", source: "NHC GIS", sourceUrl: "https://www.nhc.noaa.gov/gis/", detail: "Published forecast 34-knot wind fields support exposure screening when available." },
  ],
  historical: [
    { id: "earthquake", state: "connected", source: "USGS ShakeMap archive", sourceUrl: "https://earthquake.usgs.gov/data/shakemap/", detail: "Only events with a published ShakeMap are runnable as source-backed exposure screens." },
    { id: "flood", state: "archive_only", source: "NOAA Storm Events archive", sourceUrl: "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/", detail: "Archive source is linked, but an approved historical flood-footprint adapter is not connected." },
    { id: "wildfire", state: "archive_only", source: "NIFC / MTBS archives", sourceUrl: "https://mtbs.gov/", detail: "Historical fire records are not currently connected as runnable perimeter geometry." },
    { id: "hurricane", state: "archive_only", source: "NOAA IBTrACS", sourceUrl: "https://www.ncei.noaa.gov/products/international-best-track-archive", detail: "Best-track records are not impact footprints and are not treated as one." },
  ],
  hypothetical: [
    { id: "flood", state: "connected", source: "FEMA NFHL", sourceUrl: "https://hazards.fema.gov/femaportal/NFHL/", detail: "U.S. regulatory flood-zone exposure screen; zone membership is not water depth or property loss." },
    { id: "earthquake", state: "not_connected", source: "USGS National Seismic Hazard Model", sourceUrl: "https://www.usgs.gov/programs/earthquake-hazards/national-seismic-hazard-model", detail: "A probabilistic shaking model has not been connected to an approved exposure and vulnerability workflow." },
    { id: "hurricane", state: "not_connected", source: "NOAA hurricane archives", sourceUrl: "https://www.nhc.noaa.gov/data/", detail: "No approved probabilistic wind-field model is connected in this release." },
    { id: "wildfire", state: "not_connected", source: "USFS Wildfire Hazard Potential", sourceUrl: "https://www.firelab.org/project/wildfire-hazard-potential", detail: "Hazard potential is not a return-period event field and is not presented as one." },
  ],
};

const DEFAULT_HAZARD: Record<RunnableMode, AnalysisHazard> = {
  live: "earthquake",
  historical: "earthquake",
  hypothetical: "flood",
};

const PROGRESS = [
  "Loading authoritative event",
  "Processing hazard footprint",
  "Finding affected locations",
  "Loading structures",
  "Checking exposure response",
  "Applying validity gates",
  "Finalizing audit manifest",
];

function defaultThreshold(hazard: AnalysisHazard) {
  if (hazard === "earthquake") return "MMI IV+";
  if (hazard === "hurricane") return "Official forecast 34-knot wind field";
  if (hazard === "wildfire") return "Observed mapped fire perimeter";
  return "Authoritative hazard footprint";
}

export function ModelBuilder({ location, onRequestLocation, onDemo, onResult, onNotice }: Props) {
  const [mode, setMode] = useState<RunnableMode>("hypothetical");
  const [hazard, setHazard] = useState<AnalysisHazard>("flood");
  const [catalog, setCatalog] = useState<HazardEventSearchResponse | null>(null);
  const [eventId, setEventId] = useState("");
  const [threshold, setThreshold] = useState("Authoritative hazard footprint");
  const [returnPeriod, setReturnPeriod] = useState(100);
  const [startDate, setStartDate] = useState(() => new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(0);
  const [runError, setRunError] = useState<string | null>(null);
  const [catalogRevision, setCatalogRevision] = useState(0);
  const capability = HAZARD_CAPABILITIES[mode].find((item) => item.id === hazard) ?? HAZARD_CAPABILITIES[mode][0];
  const supportsEventCatalog = mode === "live" || (mode === "historical" && capability.state === "connected");
  const supportsScenario = capability.state === "connected";

  useEffect(() => {
    if (!supportsEventCatalog) {
      return;
    }
    let cancelled = false;
    void api.hazardEvents(mode, hazard, startDate, endDate)
      .then((response) => {
        if (!cancelled) setCatalog(response);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message = error instanceof ApiError
          ? error.message
          : "The authoritative catalog could not be loaded. No substitute event was used.";
        setCatalog({ events: [], provider: "Unavailable", retrieved_at: new Date().toISOString(), data_status: "unavailable", message });
      })
      .finally(() => {
        if (!cancelled) setLoadingEvents(false);
      });
    return () => { cancelled = true; };
  }, [catalogRevision, mode, hazard, startDate, endDate, supportsEventCatalog]);

  function changeMode(next: RunnableMode) {
    const nextHazard = DEFAULT_HAZARD[next];
    setMode(next);
    setHazard(nextHazard);
    setThreshold(defaultThreshold(nextHazard));
    setEventId("");
    setCatalog(null);
    setLoadingEvents(next === "live" || next === "historical");
    setRunError(null);
  }

  function changeHazard(next: AnalysisHazard) {
    setHazard(next);
    setThreshold(defaultThreshold(next));
    setEventId("");
    setCatalog(null);
    setLoadingEvents(mode !== "hypothetical");
    setRunError(null);
  }

  function refreshCatalog() {
    if (!supportsEventCatalog) return;
    setEventId("");
    setCatalog(null);
    setLoadingEvents(true);
    setRunError(null);
    setCatalogRevision((revision) => revision + 1);
  }

  const runnableEvents = useMemo(() => catalog?.events.filter((event) => event.footprint_available) ?? [], [catalog]);
  const catalogOnlyCount = (catalog?.events.length ?? 0) - runnableEvents.length;
  const selectedEvent = runnableEvents.find((event) => event.provider_event_id === eventId);
  const actionLabel = mode === "hypothetical" ? "Run FEMA flood-zone screen" : "Run source-backed screen";
  const valid = useMemo(
    () => mode === "hypothetical"
      ? supportsScenario && Boolean(location) && [50, 100, 500].includes(returnPeriod)
      : supportsEventCatalog && Boolean(selectedEvent?.footprint_available),
    [location, mode, returnPeriod, selectedEvent, supportsEventCatalog, supportsScenario],
  );
  const exposureStep = mode === "hypothetical" || mode === "historical" ? 5 : 4;
  const vulnerabilityStep = exposureStep + 1;

  async function run() {
    if (!valid || running) return;
    setRunning(true);
    setRunError(null);
    setStage(0);
    const timer = window.setInterval(() => setStage((value) => Math.min(value + 1, PROGRESS.length - 1)), 900);
    try {
      const result = await api.runAnalysis({
        mode,
        hazard_type: hazard,
        location,
        provider: selectedEvent?.provider,
        event_id: eventId || null,
        advisory_id: selectedEvent?.advisory_id,
        threshold: mode === "hypothetical" ? `${returnPeriod}-year / ${100 / returnPeriod}% AEP` : threshold,
        return_period_years: mode === "hypothetical" ? returnPeriod : null,
        start_date: mode === "historical" ? startDate : null,
        end_date: mode === "historical" ? endDate : null,
        vulnerability_model: null,
        simulation_count: 1000,
        seed: 12345,
      });
      onResult(result);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "The analysis service could not be reached.";
      setRunError(`${message} You can retry without re-entering the scenario.`);
      onNotice(`${message} No result or replacement values were invented.`);
    } finally {
      window.clearInterval(timer);
      setRunning(false);
    }
  }

  return <section className="floating-card scenario-card workflow-card" data-testid="model-builder">
    <div className="card-heading">
      <div><span className="eyebrow">Runnable CAT workflows</span><h2>Build a risk scenario</h2></div>
      <button className="sample-link" type="button" onClick={() => void onDemo()}><FlaskConical size={14} />Use sample demonstration</button>
    </div>

    <div className="workflow-coverage" role="status">
      <CheckCircle2 size={15} />
      <span><strong>Connected now</strong>NWS flood alerts · NHC wind · USGS ShakeMap · NIFC fire · FEMA flood zones</span>
    </div>

    <fieldset className="mode-selector">
      <legend>Analysis mode</legend>
      <div>{MODES.map((item) => <button type="button" key={item.id} className={mode === item.id ? "selected" : ""} onClick={() => changeMode(item.id)} aria-pressed={mode === item.id}>
        {item.id === "live" ? <Radio size={14} /> : item.id === "historical" ? <CalendarDays size={14} /> : <FlaskConical size={14} />}
        <span>{item.label}<small>{item.detail}</small></span>
      </button>)}</div>
    </fieldset>

    <label>1 · Hazard type
      <select data-testid="hazard-select" value={hazard} onChange={(event) => changeHazard(event.target.value as AnalysisHazard)}>
        {HAZARD_CAPABILITIES[mode].map((item) => <option key={item.id} value={item.id}>{HAZARD_LABELS[item.id]}{item.state === "connected" ? " — connected" : item.state === "archive_only" ? " — archive linked" : " — model not connected"}</option>)}
      </select>
    </label>

    <div className={`hazard-capability ${capability.state}`} role="status">
      <span>{capability.state === "connected" ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}</span>
      <div><strong>{capability.state === "connected" ? `${capability.source} connected` : capability.state === "archive_only" ? `${capability.source} archive linked` : `${capability.source} not connected`}</strong><p>{capability.detail}</p></div>
      <a href={capability.sourceUrl} target="_blank" rel="noreferrer">Source</a>
    </div>

    {mode === "historical" && supportsEventCatalog && <div className="date-fields">
      <label>2 · Start date<input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setEventId(""); setCatalog(null); setLoadingEvents(true); setRunError(null); }} /></label>
      <label>End date<input type="date" value={endDate} min={startDate} onChange={(event) => { setEndDate(event.target.value); setEventId(""); setCatalog(null); setLoadingEvents(true); setRunError(null); }} /></label>
    </div>}

    {mode !== "hypothetical" && supportsEventCatalog && <>
      <label>{mode === "live" ? "2 · Runnable event" : "3 · Runnable historical event"}
        <select data-testid="event-select" value={eventId} disabled={loadingEvents} onChange={(event) => { setEventId(event.target.value); setRunError(null); }}>
          <option value="">{loadingEvents ? "Loading authoritative catalog…" : runnableEvents.length ? "Select an event with a footprint" : "No runnable footprint available"}</option>
          {runnableEvents.map((event) => <option key={event.provider_event_id} value={event.provider_event_id}>{event.name}</option>)}
        </select>
      </label>
      {!loadingEvents && runnableEvents.length > 0 && <div className="runnable-event-summary" role="status">
        <span><CheckCircle2 size={14} /><strong>{runnableEvents.length} footprint-ready event{runnableEvents.length === 1 ? "" : "s"}</strong><small>from {catalog?.provider ?? "the authoritative provider"}</small></span>
        <div>
          <button type="button" onClick={() => { setEventId(runnableEvents[0].provider_event_id); setRunError(null); }}>Use first ready</button>
          <button type="button" aria-label="Refresh authoritative events" onClick={refreshCatalog}><RefreshCw size={13} />Refresh</button>
        </div>
      </div>}
      {!loadingEvents && runnableEvents.length > 0 && <div className="runnable-event-list" aria-label="Footprint-ready events">
        {runnableEvents.slice(0, 4).map((event) => <button type="button" key={event.provider_event_id} className={eventId === event.provider_event_id ? "selected" : ""} onClick={() => { setEventId(event.provider_event_id); setRunError(null); }}>
          <strong>{event.name}</strong>
          <span>{event.classification} · {event.update_time ? new Date(event.update_time).toLocaleString() : "Update time not reported"}</span>
        </button>)}
      </div>}
      {!loadingEvents && catalogOnlyCount > 0 && <div className="catalog-note"><AlertCircle size={14} /><span><strong>{catalogOnlyCount} catalog record{catalogOnlyCount === 1 ? "" : "s"} hidden</strong>{hazard === "earthquake" ? "Epicentres without a published ShakeMap are not runnable impact areas." : "Alerts without a published polygon are not runnable spatial screen areas."}</span></div>}
      {!loadingEvents && runnableEvents.length === 0 && <div className="workflow-message"><AlertCircle size={15} /><span>{catalog?.message ?? "The provider returned no event with a usable footprint. Try another connected mode or date range."}</span></div>}
      {mode === "historical" && <p className="historical-scope-note">The USGS connection runs only events with published ShakeMap geometry. Flood, cyclone and wildfire archives remain visible in Genome Lab and the linked official sources, but are not silently converted into impact footprints.</p>}
      {selectedEvent && <div className="event-provenance">
        <strong>{selectedEvent.provider} · {selectedEvent.classification}</strong>
        <span>Updated {selectedEvent.update_time ? new Date(selectedEvent.update_time).toLocaleString() : "not reported"}</span>
        <span>Published source geometry available</span>
      </div>}
      <label>{mode === "live" ? "3 · Impact threshold" : "4 · Event threshold"}
        <select value={threshold} onChange={(event) => setThreshold(event.target.value)}>
          {hazard === "earthquake" && <><option>MMI IV+</option><option>MMI VI+</option><option>MMI VII+</option><option>MMI VIII+</option></>}
          {hazard === "hurricane" && <option>Official forecast 34-knot wind field</option>}
          {hazard === "wildfire" && <option>Observed mapped fire perimeter</option>}
          {hazard === "flood" && <option>NWS alert-area polygon</option>}
        </select>
      </label>
    </>}

    {mode !== "hypothetical" && !supportsEventCatalog && <div className="workflow-message archive-message"><AlertCircle size={15} /><span><strong>Not runnable in this release.</strong> This view links to the official archive so you can inspect the record, but RiskChain has no approved historical {HAZARD_LABELS[hazard].toLowerCase()} geometry adapter. It will not manufacture a footprint, fragility curve, or loss result.</span></div>}

    {mode === "hypothetical" && <>
      {supportsScenario ? <>
        <label>2 · Location<button className="location-picker" type="button" onClick={onRequestLocation}><Search size={14} />{location ? location.name : "Search and select a U.S. location"}</button></label>
        {location && <div className="geography-proof"><CheckCircle2 size={15} /><span><strong>{location.county ?? "County not available"}</strong>{location.tract ? `${location.tract} · GEOID ${location.tract_geoid}` : "Census tract not available"}</span></div>}
        <label>3 · Scenario type<select aria-label="Scenario type"><option>FEMA effective flood-hazard area</option></select></label>
        <label>4 · Return period<select value={returnPeriod} onChange={(event) => { setReturnPeriod(Number(event.target.value)); setRunError(null); }}><option value={50}>50-year flood — 2% annual exceedance probability</option><option value={100}>100-year flood — 1% annual exceedance probability</option><option value={500}>500-year flood — 0.2% annual exceedance probability</option></select></label>
      </> : <div className="workflow-message archive-message"><AlertCircle size={15} /><span><strong>Return-period model not connected.</strong> A return period is hazard-specific. RiskChain currently has a FEMA flood-zone screen only; it does not relabel seismic hazard, hurricane history, or wildfire potential as an approved return-period event.</span></div>}
    </>}

    {supportsScenario && <>
      <label>{exposureStep} · Exposure<select><option>USACE National Structure Inventory 2026 Base</option></select></label>
      <label>{vulnerabilityStep} · Vulnerability<select disabled><option>Applied only when compatible asset intensity exists</option></select></label>
      <div className="assumption-note"><Database size={16} /><span><strong>Validity gate</strong>If defensible asset-level intensity is missing, RiskChain returns exposure screening—not a dollar-loss estimate.</span></div>
    </>}
    {running && <div className="run-progress" aria-live="polite">{PROGRESS.map((item, index) => <span key={item} className={index <= stage ? "active" : ""}><i />{item}</span>)}</div>}
    {runError && <div className="run-error" role="alert"><AlertCircle size={15} /><span>{runError}</span></div>}
    <button className="primary run-button" data-testid="run-analysis" type="button" disabled={!valid || running} onClick={() => void run()}><Play size={17} fill="currentColor" />
      {running ? PROGRESS[stage] : valid ? runError ? <><RefreshCw size={15} />Retry source-backed screen</> : actionLabel : !supportsScenario ? "No approved model connected" : mode === "hypothetical" ? "Select a location to continue" : loadingEvents ? "Loading authoritative events…" : "Select a footprint-ready event"}
    </button>
  </section>;
}
