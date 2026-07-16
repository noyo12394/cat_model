"use client";

import { useState } from "react";
import { Check, ChevronDown, CircleHelp, Contrast, Eye, Globe2, Layers3, LocateFixed, X } from "lucide-react";
import { useAppStore, type HazardFilterKey } from "@/lib/store";

const LAYER_META = {
  hazards: { label: "Hazards", detail: "Multi-hazard signals and warnings", tone: "#f97355" },
  infrastructure: { label: "Infrastructure", detail: "Hospitals, bridges and gauges", tone: "#38bdf8" },
  population: { label: "Community context", detail: "Exposure and vulnerability", tone: "#c4b5fd" },
  intelligence: { label: "Impact outlook", detail: "Possible effects over time", tone: "#fbbf24" },
  imagery: { label: "Quiet basemap", detail: "Reduce labels and visual noise", tone: "#86efac" },
} as const;

const HAZARD_META: { key: HazardFilterKey; label: string; tone: string }[] = [
  { key: "weather", label: "Weather", tone: "#60a5fa" },
  { key: "flood", label: "Flood", tone: "#22d3ee" },
  { key: "earthquake", label: "Quake", tone: "#fb923c" },
  { key: "wildfire", label: "Fire", tone: "#fb7185" },
  { key: "air", label: "Air", tone: "#c4b5fd" },
  { key: "landslide", label: "Landslide", tone: "#d6b37a" },
];

export function MapControls() {
  const [layersOpen, setLayersOpen] = useState(false);
  const [legendOpen, setLegendOpen] = useState(false);
  const layers = useAppStore((s) => s.layers);
  const toggleLayer = useAppStore((s) => s.toggleLayer);
  const hazardFilters = useAppStore((s) => s.hazardFilters);
  const toggleHazardFilter = useAppStore((s) => s.toggleHazardFilter);
  const uncertaintyLens = useAppStore((s) => s.uncertaintyLens);
  const toggleUncertaintyLens = useAppStore((s) => s.toggleUncertaintyLens);
  const highContrast = useAppStore((s) => s.highContrast);
  const toggleHighContrast = useAppStore((s) => s.toggleHighContrast);
  const flyTo = useAppStore((s) => s.flyTo);
  const mapScope = useAppStore((s) => s.mapScope);
  const setMapScope = useAppStore((s) => s.setMapScope);
  const setOffsetMinutes = useAppStore((s) => s.setOffsetMinutes);
  const setPanel = useAppStore((s) => s.setPanel);
  const enabledCount = Object.values(layers).filter(Boolean).length;

  return (
    <div className="map-controls" aria-label="Map controls">
      <div className="control-group">
        <button
          type="button"
          className={`map-control-button map-control-wide ${layersOpen ? "is-active" : ""}`}
          onClick={() => setLayersOpen((value) => !value)}
          aria-expanded={layersOpen}
          aria-controls="layer-manager"
        >
          <Layers3 size={17} aria-hidden /> Layers <span className="control-count">{enabledCount}</span>
          <ChevronDown size={14} aria-hidden />
        </button>
        <button
          type="button"
          className={`map-control-button map-control-wide ${mapScope === "global" ? "is-active" : ""}`}
          onClick={() => {
            const next = mapScope === "global" ? "local" : "global";
            setMapScope(next);
            if (next === "global") setOffsetMinutes(0);
            flyTo(next === "global" ? [8, 18] : [-75.3705, 40.6259], next === "global" ? 1.45 : 12);
            setPanel(next === "global" ? { kind: "global-events" } : { kind: "region-summary" });
          }}
          aria-pressed={mapScope === "global"}
          aria-label={mapScope === "global" ? "Return to regional view" : "Open global GDACS events"}
        >
          <Globe2 size={17} aria-hidden /> {mapScope === "global" ? "Regional" : "Global"}
        </button>
        <button
          type="button"
          className={`map-control-button ${uncertaintyLens ? "is-active" : ""}`}
          onClick={toggleUncertaintyLens}
          aria-pressed={uncertaintyLens}
          aria-label="Toggle uncertainty lens"
          title="Show where information is sparse, stale, or conflicting"
        >
          <Eye size={17} aria-hidden />
        </button>
        <button
          type="button"
          className="map-control-button"
          onClick={() => { setMapScope("local"); flyTo([-75.3705, 40.6259], 12); setPanel({ kind: "region-summary" }); }}
          aria-label="Return to Lehigh Valley overview"
          title="Return to regional overview"
        >
          <LocateFixed size={17} aria-hidden />
        </button>
        <button
          type="button"
          className={`map-control-button ${legendOpen ? "is-active" : ""}`}
          onClick={() => setLegendOpen((value) => !value)}
          aria-expanded={legendOpen}
          aria-label="Open map legend"
          title="Map legend"
        >
          <CircleHelp size={17} aria-hidden />
        </button>
        <button
          type="button"
          className={`map-control-button ${highContrast ? "is-active" : ""}`}
          onClick={toggleHighContrast}
          aria-pressed={highContrast}
          aria-label="Toggle high contrast mode"
          title="High contrast mode"
        >
          <Contrast size={17} aria-hidden />
        </button>
      </div>

      {layersOpen && (
        <section id="layer-manager" className="layer-manager" aria-label="Map layers">
          <div className="layer-manager-header">
            <div>
              <span className="panel-kicker">MAP CONTENT</span>
              <h2>Layers</h2>
            </div>
            <button type="button" className="icon-button" onClick={() => setLayersOpen(false)} aria-label="Close layers">
              <X size={16} aria-hidden />
            </button>
          </div>
          <p className="layer-intro">Turn context on only when it helps answer your question.</p>
          <div className="hazard-filter-block">
            <span className="panel-kicker">HAZARD SIGNALS</span>
            <div className="hazard-filter-grid">
              {HAZARD_META.map((hazard) => (
                <button key={hazard.key} type="button" className={hazardFilters[hazard.key] ? "is-enabled" : ""} onClick={() => toggleHazardFilter(hazard.key)} aria-pressed={hazardFilters[hazard.key]}>
                  <i style={{ background: hazard.tone }} aria-hidden /> {hazard.label}
                </button>
              ))}
            </div>
          </div>
          <div className="layer-list">
            {(Object.keys(LAYER_META) as (keyof typeof LAYER_META)[]).map((key) => {
              const item = LAYER_META[key];
              return (
                <button
                  key={key}
                  type="button"
                  className={`layer-row ${layers[key] ? "is-enabled" : ""}`}
                  onClick={() => toggleLayer(key)}
                  aria-pressed={layers[key]}
                >
                  <span className="layer-swatch" style={{ backgroundColor: item.tone }} aria-hidden />
                  <span className="layer-copy"><strong>{item.label}</strong><small>{item.detail}</small></span>
                  <span className="layer-check" aria-hidden>{layers[key] && <Check size={13} />}</span>
                </button>
              );
            })}
          </div>
          <button type="button" className={`uncertainty-callout ${uncertaintyLens ? "is-active" : ""}`} onClick={toggleUncertaintyLens}>
            <Eye size={17} aria-hidden />
            <span><strong>Uncertainty lens</strong><small>Reveal missing and conflicting evidence</small></span>
            <span className="toggle-track" aria-hidden><span /></span>
          </button>
        </section>
      )}

      {legendOpen && (
        <section className="map-legend" aria-label="Map legend">
          <div className="legend-heading"><strong>How to read the map</strong><button type="button" onClick={() => setLegendOpen(false)} aria-label="Close legend"><X size={14} /></button></div>
          <div><span className="legend-symbol solid" /> Observed</div>
          <div><span className="legend-symbol outline" /> Official alert</div>
          <div><span className="legend-symbol dashed" /> Forecast</div>
          <div><span className="legend-symbol dotted" /> AI-inferred impact</div>
        </section>
      )}
    </div>
  );
}
