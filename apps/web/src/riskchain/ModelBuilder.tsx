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
  { id: "live", label: "Live event", detail: "NHC · USGS · NIFC" },
  { id: "historical", label: "Historical", detail: "USGS ShakeMap" },
  { id: "hypothetical", label: "Return period", detail: "FEMA flood" },
];

const HAZARD_LABELS: Record<AnalysisHazard, string> = {
  hurricane: "Tropical cyclone",
  earthquake: "Earthquake",
  flood: "Flood",
  wildfire: "Wildfire",
};

// This is deliberately narrower than the product roadmap. Every option shown
// here has an authoritative provider and an executable backend path today.
const RUNNABLE_HAZARDS: Record<RunnableMode, AnalysisHazard[]> = {
  // Default to the fastest, most consistently available adapter. NHC and NIFC
  // remain selectable, but a new Live workflow should never open on an empty
  // or slow catalog by default.
  live: ["earthquake", "wildfire", "hurricane"],
  historical: ["earthquake"],
  hypothetical: ["flood"],
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

  useEffect(() => {
    if (mode === "hypothetical") return;
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
  }, [catalogRevision, mode, hazard, startDate, endDate]);

  function changeMode(next: RunnableMode) {
    const nextHazard = RUNNABLE_HAZARDS[next][0];
    setMode(next);
    setHazard(nextHazard);
    setThreshold(defaultThreshold(nextHazard));
    setEventId("");
    setCatalog(null);
    setLoadingEvents(next !== "hypothetical");
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
    if (mode === "hypothetical") return;
    setEventId("");
    setCatalog(null);
    setLoadingEvents(true);
    setRunError(null);
    setCatalogRevision((revision) => revision + 1);
  }

  const runnableEvents = useMemo(() => catalog?.events.filter((event) => event.footprint_available) ?? [], [catalog]);
  const catalogOnlyCount = (catalog?.events.length ?? 0) - runnableEvents.length;
  const selectedEvent = runnableEvents.find((event) => event.provider_event_id === eventId);
  const actionLabel = mode === "hypothetical" ? "Run flood exposure screen" : "Run source-backed screen";
  const valid = useMemo(
    () => mode === "hypothetical"
      ? Boolean(location) && [50, 100, 500].includes(returnPeriod)
      : Boolean(selectedEvent?.footprint_available),
    [location, mode, returnPeriod, selectedEvent],
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
      <span><strong>Connected now</strong>NHC wind · USGS ShakeMap · NIFC fire · FEMA flood</span>
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
        {RUNNABLE_HAZARDS[mode].map((id) => <option key={id} value={id}>{HAZARD_LABELS[id]}</option>)}
      </select>
    </label>

    {mode === "historical" && <div className="date-fields">
      <label>2 · Start date<input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setEventId(""); setCatalog(null); setLoadingEvents(true); setRunError(null); }} /></label>
      <label>End date<input type="date" value={endDate} min={startDate} onChange={(event) => { setEndDate(event.target.value); setEventId(""); setCatalog(null); setLoadingEvents(true); setRunError(null); }} /></label>
    </div>}

    {mode !== "hypothetical" && <>
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
      {!loadingEvents && catalogOnlyCount > 0 && <div className="catalog-note"><AlertCircle size={14} /><span><strong>{catalogOnlyCount} catalog event{catalogOnlyCount === 1 ? "" : "s"} hidden</strong>Epicentres without a published ShakeMap are not runnable impact areas.</span></div>}
      {!loadingEvents && runnableEvents.length === 0 && <div className="workflow-message"><AlertCircle size={15} /><span>{catalog?.message ?? "The provider returned no event with a usable footprint. Try another connected mode or date range."}</span></div>}
      {mode === "historical" && <p className="historical-scope-note">Historical flood, cyclone, wildfire and earthquake records can be explored in Genome Lab. Only USGS events with a published ShakeMap are currently eligible for a source-backed exposure screen.</p>}
      {selectedEvent && <div className="event-provenance">
        <strong>{selectedEvent.provider} · {selectedEvent.classification}</strong>
        <span>Updated {selectedEvent.update_time ? new Date(selectedEvent.update_time).toLocaleString() : "not reported"}</span>
        <span>Published impact footprint advertised</span>
      </div>}
      <label>{mode === "live" ? "3 · Impact threshold" : "4 · Event threshold"}
        <select value={threshold} onChange={(event) => setThreshold(event.target.value)}>
          {hazard === "earthquake" && <><option>MMI IV+</option><option>MMI VI+</option><option>MMI VII+</option><option>MMI VIII+</option></>}
          {hazard === "hurricane" && <option>Official forecast 34-knot wind field</option>}
          {hazard === "wildfire" && <option>Observed mapped fire perimeter</option>}
        </select>
      </label>
    </>}

    {mode === "hypothetical" && <>
      <label>2 · Location<button className="location-picker" type="button" onClick={onRequestLocation}><Search size={14} />{location ? location.name : "Search and select a U.S. location"}</button></label>
      {location && <div className="geography-proof"><CheckCircle2 size={15} /><span><strong>{location.county ?? "County not available"}</strong>{location.tract ? `${location.tract} · GEOID ${location.tract_geoid}` : "Census tract not available"}</span></div>}
      <label>3 · Scenario type<select aria-label="Scenario type"><option>FEMA effective flood-hazard area</option></select></label>
      <label>4 · Return period<select value={returnPeriod} onChange={(event) => { setReturnPeriod(Number(event.target.value)); setRunError(null); }}><option value={50}>50-year flood — 2% annual exceedance probability</option><option value={100}>100-year flood — 1% annual exceedance probability</option><option value={500}>500-year flood — 0.2% annual exceedance probability</option></select></label>
    </>}

    <label>{exposureStep} · Exposure<select><option>USACE National Structure Inventory 2026 Base</option></select></label>
    <label>{vulnerabilityStep} · Vulnerability<select disabled><option>Applied only when compatible asset intensity exists</option></select></label>
    <div className="assumption-note"><Database size={16} /><span><strong>Validity gate</strong>If defensible asset-level intensity is missing, RiskChain returns exposure screening—not a dollar-loss estimate.</span></div>
    {running && <div className="run-progress" aria-live="polite">{PROGRESS.map((item, index) => <span key={item} className={index <= stage ? "active" : ""}><i />{item}</span>)}</div>}
    {runError && <div className="run-error" role="alert"><AlertCircle size={15} /><span>{runError}</span></div>}
    <button className="primary run-button" data-testid="run-analysis" type="button" disabled={!valid || running} onClick={() => void run()}><Play size={17} fill="currentColor" />
      {running ? PROGRESS[stage] : valid ? runError ? <><RefreshCw size={15} />Retry source-backed screen</> : actionLabel : mode === "hypothetical" ? "Select a location to continue" : loadingEvents ? "Loading authoritative events…" : "Select a footprint-ready event"}
    </button>
  </section>;
}
