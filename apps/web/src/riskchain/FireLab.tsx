"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Download,
  ExternalLink,
  Flame,
  Layers3,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { AnalysisRunResult, HazardEventSearchResponse, HazardEventSummary } from "@/lib/types";

type Props = {
  analysis: AnalysisRunResult | null;
  perimeterVisible: boolean;
  perimeterOpacity: number;
  onAnalysisChange: (analysis: AnalysisRunResult | null) => void;
  onPerimeterVisibleChange: (visible: boolean) => void;
  onPerimeterOpacityChange: (opacity: number) => void;
  onIncidentFocus?: (incident: HazardEventSummary) => void;
  onNotice?: (message: string) => void;
};

function formatUtc(value?: string | null) {
  if (!value) return "Not reported";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Not reported";
  return `${new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(parsed)} UTC`;
}

function downloadManifest(analysis: AnalysisRunResult) {
  const blob = new Blob([JSON.stringify(analysis.manifest, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${analysis.run_id}-wildfire-screening-manifest.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function FireLab({
  analysis,
  perimeterVisible,
  perimeterOpacity,
  onAnalysisChange,
  onPerimeterVisibleChange,
  onPerimeterOpacityChange,
  onIncidentFocus,
  onNotice,
}: Props) {
  const [catalog, setCatalog] = useState<HazardEventSearchResponse | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingPerimeter, setLoadingPerimeter] = useState(false);
  const [catalogRevision, setCatalogRevision] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void api.hazardEvents("live", "wildfire")
      .then((response) => {
        if (cancelled) return;
        setCatalog(response);
        setSelectedId((current) => response.events.some((event) => event.provider_event_id === current)
          ? current
          : response.events.find((event) => event.footprint_available)?.provider_event_id ?? "");
      })
      .catch((requestError: unknown) => {
        if (cancelled) return;
        const message = requestError instanceof ApiError
          ? requestError.message
          : "The NIFC active-perimeter catalog could not be reached.";
        setCatalog({
          events: [],
          provider: "National Interagency Fire Center",
          retrieved_at: new Date().toISOString(),
          data_status: "unavailable",
          message,
        });
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => { cancelled = true; };
  }, [catalogRevision]);

  const runnableIncidents = useMemo(
    () => catalog?.events.filter((event) => event.footprint_available) ?? [],
    [catalog],
  );
  const selectedIncident = useMemo(
    () => runnableIncidents.find((event) => event.provider_event_id === selectedId) ?? null,
    [runnableIncidents, selectedId],
  );
  const selectedAnalysis = analysis?.hazard_type === "wildfire" && analysis.provider_event_id === selectedId
    ? analysis
    : null;
  const perimeterLoaded = Boolean(selectedAnalysis?.hazard_layers.length);

  function chooseIncident(eventId: string) {
    const next = runnableIncidents.find((incident) => incident.provider_event_id === eventId) ?? null;
    setSelectedId(eventId);
    setError(null);
    onPerimeterVisibleChange(false);
    onAnalysisChange(null);
    if (next) onIncidentFocus?.(next);
  }

  function refreshCatalog() {
    setError(null);
    setLoadingCatalog(true);
    onPerimeterVisibleChange(false);
    onAnalysisChange(null);
    setCatalogRevision((revision) => revision + 1);
  }

  async function loadPerimeter() {
    if (!selectedIncident || loadingPerimeter) return;
    setLoadingPerimeter(true);
    setError(null);
    try {
      const result = await api.runAnalysis({
        mode: "live",
        hazard_type: "wildfire",
        provider: selectedIncident.provider,
        event_id: selectedIncident.provider_event_id,
        advisory_id: selectedIncident.advisory_id,
        threshold: "Observed mapped fire perimeter",
        exposure_dataset: "USACE National Structure Inventory 2026 Base",
        vulnerability_model: null,
        simulation_count: 1000,
        seed: 12345,
      });
      onAnalysisChange(result);
      onIncidentFocus?.(selectedIncident);
      if (result.hazard_layers.length > 0) {
        onPerimeterVisibleChange(true);
      } else {
        onPerimeterVisibleChange(false);
        setError("NIFC returned the incident record, but no usable official perimeter geometry was available. The audit manifest remains downloadable.");
      }
    } catch (requestError) {
      const message = requestError instanceof ApiError
        ? requestError.message
        : "The official wildfire perimeter could not be loaded.";
      onPerimeterVisibleChange(false);
      setError(`${message} No replacement boundary was drawn.`);
      onNotice?.(`${message} No replacement boundary was drawn.`);
    } finally {
      setLoadingPerimeter(false);
    }
  }

  async function togglePerimeter() {
    if (perimeterVisible) {
      onPerimeterVisibleChange(false);
      return;
    }
    if (perimeterLoaded) {
      onPerimeterVisibleChange(true);
      return;
    }
    await loadPerimeter();
  }

  const status = loadingCatalog
    ? "checking NIFC"
    : catalog?.data_status === "live"
      ? "official feed connected"
      : "official feed unavailable";

  return <section className="fire-lab-card" aria-label="FIRE Lab wildfire perimeter viewer" data-testid="fire-lab">
    <header className="fire-lab-head">
      <div>
        <span className="eyebrow"><Flame size={13} /> Day 4 · source-backed wildfire screen</span>
        <h1>FIRE Lab</h1>
        <p>Choose an active NIFC incident and display its published perimeter. The boundary supports exposure screening only; it is not fire intensity, spread, damage, or loss.</p>
      </div>
      <Link className="fire-history-link" href="/historic/camp-fire-2018/burn-perimeter">
        Camp Fire 2018 archive <ExternalLink size={14} />
      </Link>
    </header>

    <div className={`fire-source-status ${catalog?.data_status ?? "loading"}`} role="status">
      {loadingCatalog ? <LoaderCircle className="spin" size={16} /> : catalog?.data_status === "live" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
      <span><strong>{status}</strong><small>{catalog?.provider ?? "National Interagency Fire Center"} · checked {formatUtc(catalog?.retrieved_at)}</small></span>
      <button type="button" onClick={refreshCatalog} disabled={loadingCatalog}>
        <RefreshCw size={14} /> Refresh incidents
      </button>
      <small className="control-impact">Checks NIFC again and clears the currently displayed perimeter.</small>
    </div>

    <div className="fire-controls">
      <label className="fire-control">
        <span>Active incident</span>
        <select value={selectedId} onChange={(event) => chooseIncident(event.target.value)} disabled={loadingCatalog || runnableIncidents.length === 0}>
          <option value="">{loadingCatalog ? "Loading active NIFC incidents…" : runnableIncidents.length ? "Select an incident…" : "No mapped active perimeter available"}</option>
          {runnableIncidents.map((incident) => <option key={incident.provider_event_id} value={incident.provider_event_id}>{incident.name} · {incident.status}</option>)}
        </select>
        <small>Changes the incident the map focuses on and the official perimeter that can be loaded.</small>
      </label>

      <div className="fire-control fire-layer-toggle">
        <span>Official perimeter</span>
        <button
          type="button"
          role="switch"
          aria-checked={perimeterVisible && perimeterLoaded}
          className={perimeterVisible && perimeterLoaded ? "active" : ""}
          disabled={!selectedIncident || loadingPerimeter}
          onClick={() => void togglePerimeter()}
        >
          {loadingPerimeter ? <LoaderCircle className="spin" size={15} /> : <Layers3 size={15} />}
          {loadingPerimeter ? "Loading source geometry…" : perimeterVisible && perimeterLoaded ? "Hide perimeter" : "Show perimeter"}
        </button>
        <small>Shows or hides the exact NIFC boundary; it does not change or recalculate the geometry.</small>
      </div>

      <label className="fire-control fire-opacity">
        <span>Perimeter opacity <strong>{Math.round(perimeterOpacity * 100)}%</strong></span>
        <input
          type="range"
          min="10"
          max="90"
          step="5"
          value={Math.round(perimeterOpacity * 100)}
          disabled={!perimeterVisible || !perimeterLoaded}
          onChange={(event) => onPerimeterOpacityChange(Number(event.target.value) / 100)}
        />
        <small>Changes boundary transparency on the map only; the source data stay unchanged.</small>
      </label>
    </div>

    {selectedIncident && <section className="fire-incident-summary">
      <div><span className={`provenance ${selectedIncident.classification}`}>{selectedIncident.classification} · official source</span><h2>{selectedIncident.name}</h2><p>{selectedIncident.status}</p></div>
      <dl>
        <div><dt>Provider</dt><dd>{selectedIncident.provider}</dd></div>
        <div><dt>Updated</dt><dd>{formatUtc(selectedIncident.update_time)}</dd></div>
        <div><dt>Map meaning</dt><dd>Observed mapped fire boundary</dd></div>
      </dl>
      {selectedIncident.limitations[0] && <p className="fire-limit"><ShieldCheck size={13} /> {selectedIncident.limitations[0]}</p>}
      <a href={selectedIncident.source_url} target="_blank" rel="noreferrer">Open NIFC source <ExternalLink size={13} /></a>
    </section>}

    {!loadingCatalog && catalog?.data_status === "live" && runnableIncidents.length === 0 && <div className="fire-empty">
      <ShieldCheck size={18} />
      <span><strong>No active mapped perimeter returned</strong>{catalog.message ?? "NIFC responded successfully, but no footprint-ready incident qualified."}</span>
    </div>}
    {!loadingCatalog && catalog?.data_status === "unavailable" && <div className="fire-empty error">
      <AlertTriangle size={18} />
      <span><strong>NIFC perimeter service unavailable</strong>{catalog.message ?? "No substitute incident or boundary is shown."}</span>
    </div>}
    {error && <div className="fire-empty error" role="alert"><AlertTriangle size={18} /><span><strong>Perimeter not displayed</strong>{error}</span></div>}

    <footer className="fire-lab-footer">
      <div><Database size={15} /><span><strong>{selectedAnalysis ? `Run ${selectedAnalysis.run_id.slice(0, 16)}` : "No perimeter run yet"}</strong><small>{selectedAnalysis ? `${selectedAnalysis.hazard_layers.length} official layer · ${selectedAnalysis.result_type.replaceAll("_", " ")}` : "Show a perimeter to create a source and calculation audit."}</small></span></div>
      <button type="button" disabled={!selectedAnalysis} onClick={() => selectedAnalysis && downloadManifest(selectedAnalysis)}><Download size={14} /> Download manifest</button>
      <small className="control-impact">Downloads the exact inputs, source records, limits, and code version returned by this perimeter run.</small>
    </footer>
  </section>;
}
