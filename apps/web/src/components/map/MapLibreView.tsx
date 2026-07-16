"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useAppStore, type HazardFilterKey } from "@/lib/store";
import { useMapData } from "./useMapData";
import { facilityColor, facilityIcon } from "./facilityStyle";
import type { RouteOption } from "@/lib/types";
import { exposureColor } from "./facilityStyle";

const BETHLEHEM_CENTER: [number, number] = [-75.3705, 40.6259];

const OSM_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export function MapLibreView({ route }: { route?: RouteOption[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const { facilities, incidents, sensors, compoundEvents, globalEvents, globalWatchItems } = useMapData();
  const flyToTarget = useAppStore((s) => s.flyToTarget);
  const layers = useAppStore((s) => s.layers);
  const hazardFilters = useAppStore((s) => s.hazardFilters);
  const uncertaintyLens = useAppStore((s) => s.uncertaintyLens);
  const offsetMinutes = useAppStore((s) => s.time.offsetMinutes);
  const setPanel = useAppStore((s) => s.setPanel);
  const selectGlobalEvent = useAppStore((s) => s.selectGlobalEvent);
  const mapScope = useAppStore((s) => s.mapScope);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: OSM_STYLE,
      center: BETHLEHEM_CENTER,
      zoom: 12,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    map.on("load", () => {
      map.addSource("incident-geometry", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "incident-fill",
        type: "fill",
        source: "incident-geometry",
        paint: { "fill-color": "#d13b3b", "fill-opacity": 0.15 },
      });
      map.addLayer({
        id: "incident-outline",
        type: "line",
        source: "incident-geometry",
        paint: { "line-color": "#d13b3b", "line-width": 3 },
      });

      map.addSource("global-events", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "global-event-halo",
        type: "circle",
        source: "global-events",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "priority"], 25], 0, 8, 50, 13, 100, 22],
          "circle-color": ["match", ["get", "alert"], "red", "#ff5b55", "orange", "#f6a94a", "#56ce91"],
          "circle-opacity": 0.14,
          "circle-blur": 0.35,
        },
      });
      map.addLayer({
        id: "global-event-points",
        type: "circle",
        source: "global-events",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "priority"], 25], 0, 4, 50, 6, 100, 9],
          "circle-color": ["match", ["get", "alert"], "red", "#ff5b55", "orange", "#f6a94a", "#56ce91"],
          "circle-stroke-color": "#071016",
          "circle-stroke-width": 2,
        },
      });

      map.addSource("forecast-impact", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "forecast-impact-fill",
        type: "fill",
        source: "forecast-impact",
        paint: {
          "fill-color": ["match", ["get", "band"], "likely", "#f97355", "#fbbf24"],
          "fill-opacity": ["match", ["get", "band"], "likely", 0.24, 0.1],
        },
      });
      map.addLayer({
        id: "forecast-impact-outline",
        type: "line",
        source: "forecast-impact",
        paint: {
          "line-color": ["match", ["get", "band"], "likely", "#fb7a5f", "#fbbf24"],
          "line-width": ["match", ["get", "band"], "likely", 2.5, 1.5],
          "line-dasharray": [2, 2],
        },
      });

      map.addSource("compound-surfaces", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "compound-surface-fill",
        type: "fill",
        source: "compound-surfaces",
        paint: {
          "fill-color": ["match", ["get", "group"], "weather", "#4f7cff", "flood", "#16b8d4", "landslide", "#d5a45e", "#a78bfa"],
          "fill-opacity": ["match", ["get", "certainty"], "observed", 0.22, "forecast", 0.15, 0.09],
        },
      });
      map.addLayer({
        id: "compound-surface-contour",
        type: "line",
        source: "compound-surfaces",
        paint: {
          "line-color": ["match", ["get", "group"], "weather", "#7ba2ff", "flood", "#54d8ec", "landslide", "#e6bd82", "#c4b5fd"],
          "line-width": 1.5,
          "line-opacity": 0.75,
          "line-dasharray": [2, 2],
        },
      });

      map.addSource("hazard-flow", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "hazard-flow-glow",
        type: "circle",
        source: "hazard-flow",
        paint: { "circle-radius": 13, "circle-color": "#32d8ea", "circle-opacity": 0.08, "circle-blur": 0.55 },
      });
      map.addLayer({
        id: "hazard-flow-particles",
        type: "circle",
        source: "hazard-flow",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "phase"], 0, 2.5, 1, 5],
          "circle-color": "#86f0ff",
          "circle-opacity": ["interpolate", ["linear"], ["get", "phase"], 0, 0.25, 0.55, 0.95, 1, 0.15],
          "circle-stroke-color": "#0a4752",
          "circle-stroke-width": 1,
        },
      });

      map.addSource("place-exposure", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "place-exposure-rings",
        type: "circle",
        source: "place-exposure",
        paint: {
          "circle-radius": ["match", ["get", "type"], "bridge", 20, "hospital", 17, 14],
          "circle-color": "transparent",
          "circle-stroke-color": ["match", ["get", "type"], "bridge", "#ff9f67", "hospital", "#f472b6", "#fbbf24"],
          "circle-stroke-width": 2,
          "circle-stroke-opacity": 0.7,
        },
      });

      map.addSource("sensor-points", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "sensor-halo",
        type: "circle",
        source: "sensor-points",
        paint: { "circle-radius": 12, "circle-color": "#38bdf8", "circle-opacity": 0.16 },
      });
      map.addLayer({
        id: "sensor-points-layer",
        type: "circle",
        source: "sensor-points",
        paint: {
          "circle-radius": 5,
          "circle-color": ["case", [">", ["coalesce", ["get", "trend"], 0], 0], "#fb7a5f", "#38bdf8"],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });

      map.addSource("compound-signals", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "compound-signal-halo",
        type: "circle",
        source: "compound-signals",
        paint: {
          "circle-radius": 17,
          "circle-color": ["match", ["get", "group"], "weather", "#60a5fa", "flood", "#22d3ee", "landslide", "#d6b37a", "#c4b5fd"],
          "circle-opacity": 0.14,
        },
      });
      map.addLayer({
        id: "compound-signal-points",
        type: "circle",
        source: "compound-signals",
        paint: {
          "circle-radius": 7,
          "circle-color": ["match", ["get", "group"], "weather", "#60a5fa", "flood", "#22d3ee", "landslide", "#d6b37a", "#c4b5fd"],
          "circle-stroke-color": "#071016",
          "circle-stroke-width": 3,
        },
      });

      map.addSource("community-context", { type: "geojson", data: communityContextGeoJSON() });
      map.addLayer({
        id: "community-context-fill",
        type: "fill",
        source: "community-context",
        layout: { visibility: "none" },
        paint: { "fill-color": "#8b5cf6", "fill-opacity": 0.1 },
      });
      map.addLayer({
        id: "community-context-outline",
        type: "line",
        source: "community-context",
        layout: { visibility: "none" },
        paint: { "line-color": "#a78bfa", "line-width": 1, "line-dasharray": [1, 2] },
      });

      map.addSource("uncertainty-zones", { type: "geojson", data: uncertaintyGeoJSON() });
      map.addLayer({
        id: "uncertainty-fill",
        type: "fill",
        source: "uncertainty-zones",
        layout: { visibility: "none" },
        paint: { "fill-color": "#94a3b8", "fill-opacity": 0.15 },
      });
      map.addLayer({
        id: "uncertainty-outline",
        type: "line",
        source: "uncertainty-zones",
        layout: { visibility: "none" },
        paint: { "line-color": "#cbd5e1", "line-width": 2, "line-dasharray": [1, 2] },
      });

      map.addSource("route-lines", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "route-lines-layer",
        type: "line",
        source: "route-lines",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": ["get", "color"], "line-width": 5, "line-opacity": 0.85 },
      });

      map.on("click", "incident-fill", () => setPanel({ kind: "incident", incidentId: "developing-flood-bethlehem" }));
      map.on("click", "forecast-impact-fill", () => setPanel({ kind: "incident", incidentId: "developing-flood-bethlehem" }));
      map.on("mouseenter", "incident-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "incident-fill", () => { map.getCanvas().style.cursor = ""; });
      map.on("mouseenter", "forecast-impact-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "forecast-impact-fill", () => { map.getCanvas().style.cursor = ""; });
      map.on("click", "sensor-points-layer", (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        const coordinates = feature.geometry.coordinates.slice() as [number, number];
        const wrapper = document.createElement("div");
        wrapper.className = "sensor-popup";
        const heading = document.createElement("strong");
        heading.textContent = String(feature.properties?.name ?? "Sensor observation");
        const detail = document.createElement("span");
        detail.textContent = `${feature.properties?.value ?? "—"} ${feature.properties?.unit ?? ""} · ${feature.properties?.trend_label ?? "Trend unavailable"}`;
        wrapper.append(heading, detail);
        new maplibregl.Popup({ offset: 12, closeButton: true }).setLngLat(coordinates).setDOMContent(wrapper).addTo(map);
      });
      map.on("click", "compound-signal-points", () => setPanel({ kind: "compound", eventId: "compound-flood-access-bethlehem" }));
      map.on("click", "compound-surface-fill", () => setPanel({ kind: "compound", eventId: "compound-flood-access-bethlehem" }));
      map.on("mouseenter", "compound-signal-points", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "compound-signal-points", () => { map.getCanvas().style.cursor = ""; });
      map.on("mouseenter", "compound-surface-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "compound-surface-fill", () => { map.getCanvas().style.cursor = ""; });
      map.on("click", "global-event-points", (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        const coordinates = feature.geometry.coordinates.slice() as [number, number];
        const wrapper = document.createElement("div");
        wrapper.className = "global-event-popup";
        const alert = document.createElement("span");
        alert.className = String(feature.properties?.alert ?? "green");
        alert.textContent = `${String(feature.properties?.alert ?? "green").toUpperCase()} · ${String(feature.properties?.type ?? "EVENT")}`;
        const heading = document.createElement("strong");
        heading.textContent = String(feature.properties?.name ?? "GDACS event");
        const detail = document.createElement("small");
        detail.textContent = `${String(feature.properties?.severity ?? "Severity detail unavailable")} · watch ${String(feature.properties?.priority ?? "—")}/100`;
        wrapper.append(alert, heading, detail);
        new maplibregl.Popup({ offset: 10 }).setLngLat(coordinates).setDOMContent(wrapper).addTo(map);
        selectGlobalEvent(String(feature.properties?.id ?? "") || null);
        setPanel({ kind: "global-events" });
      });
      map.on("mouseenter", "global-event-points", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "global-event-points", () => { map.getCanvas().style.cursor = ""; });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [selectGlobalEvent, setPanel]);

  // incident geometry (official-alert style: solid, strong outline)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource("incident-geometry") as maplibregl.GeoJSONSource | undefined;
      if (!src) return;
      const features = layers.hazards && mapScope === "local"
        ? incidents
            .filter((inc) => inc.geometry)
            .map((inc) => ({
              type: "Feature" as const,
              properties: { title: inc.title },
              geometry: inc.geometry as GeoJSON.Geometry,
            }))
        : [];
      src.setData({ type: "FeatureCollection", features });
    };
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [incidents, layers.hazards, mapScope]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("global-events") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData({
        type: "FeatureCollection",
        features: mapScope === "global" ? globalEvents.map((event) => ({
          type: "Feature" as const,
          properties: {
            id: event.event_id,
            name: event.name,
            alert: event.alert_level,
            type: event.event_type,
            severity: event.severity_text,
            priority: globalWatchItems.find((item) => item.event_id === event.event_id)?.priority_score ?? 25,
          },
          geometry: { type: "Point" as const, coordinates: event.center },
        })) : [],
      });
    };
    if (map.isStyleLoaded()) apply(); else map.once("load", apply);
  }, [globalEvents, globalWatchItems, mapScope]);

  // Possible future impact area. It only appears when the universal time
  // control moves into forecast time and is always rendered with dashed,
  // translucent styling to distinguish it from official observations.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("forecast-impact") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData(offsetMinutes > 0 && layers.intelligence && mapScope === "local" ? impactForecastGeoJSON(offsetMinutes) : { type: "FeatureCollection", features: [] });
    };
    if (map.isStyleLoaded()) apply(); else map.once("load", apply);
  }, [offsetMinutes, layers.intelligence, mapScope]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("sensor-points") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData({
        type: "FeatureCollection",
        features: layers.hazards && mapScope === "local" ? sensors.filter((sensor) => sensor.geometry.type === "Point").map((sensor) => ({
          type: "Feature" as const,
          properties: {
            name: sensor.sensor_name,
            value: sensor.value,
            unit: sensor.unit,
            trend: sensor.trend_per_hour ?? 0,
            trend_label: sensor.trend_per_hour != null ? `${sensor.trend_per_hour > 0 ? "+" : ""}${sensor.trend_per_hour} ${sensor.unit}/hr` : "Trend unavailable",
          },
          geometry: sensor.geometry as GeoJSON.Point,
        })) : [],
      });
    };
    if (map.isStyleLoaded()) apply(); else map.once("load", apply);
  }, [sensors, layers.hazards, mapScope]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("compound-signals") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      const features = layers.hazards && mapScope === "local" ? compoundEvents.flatMap((event) => event.signals)
        .filter((signal) => hazardFilters[toHazardFilter(signal.hazard_type)])
        .map((signal) => ({
          type: "Feature" as const,
          properties: { label: signal.label, group: toHazardFilter(signal.hazard_type), status: signal.data_status },
          geometry: { type: "Point" as const, coordinates: signal.center },
        })) : [];
      source.setData({ type: "FeatureCollection", features });
    };
    if (map.isStyleLoaded()) apply(); else map.once("load", apply);
  }, [compoundEvents, hazardFilters, layers.hazards, mapScope]);

  // Research-demo exposure surfaces follow the approximate local river and
  // terrain corridors instead of drawing arbitrary full-screen heat blobs.
  // They remain explicitly modeled, not claimed as remotely sensed truth.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("compound-surfaces") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData(layers.intelligence && layers.hazards && mapScope === "local"
        ? compoundSurfaceGeoJSON(offsetMinutes, hazardFilters)
        : { type: "FeatureCollection", features: [] });
    };
    if (map.isStyleLoaded()) apply(); else map.once("load", apply);
  }, [hazardFilters, layers.hazards, layers.intelligence, mapScope, offsetMinutes]);

  // Animated particles communicate direction only. Their speed and position
  // are illustrative and are never exposed as measured water velocity.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !layers.intelligence || !layers.hazards || !hazardFilters.flood || mapScope !== "local") return;
    let phase = 0;
    const update = () => {
      const source = map.getSource("hazard-flow") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData(flowParticlesGeoJSON(phase, offsetMinutes));
      phase = (phase + 0.07) % 1;
    };
    if (map.isStyleLoaded()) update(); else map.once("load", update);
    const timer = window.setInterval(update, 420);
    return () => {
      window.clearInterval(timer);
      const source = map.getSource("hazard-flow") as maplibregl.GeoJSONSource | undefined;
      source?.setData({ type: "FeatureCollection", features: [] });
    };
  }, [hazardFilters.flood, layers.hazards, layers.intelligence, mapScope, offsetMinutes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const source = map.getSource("place-exposure") as maplibregl.GeoJSONSource | undefined;
      if (!source) return;
      source.setData({
        type: "FeatureCollection",
        features: layers.intelligence && layers.infrastructure && mapScope === "local"
          ? facilities.filter((facility) => ["bridge", "hospital", "school"].includes(facility.facility_type)).map((facility) => ({
              type: "Feature" as const,
              properties: { id: facility.facility_id, name: facility.name, type: facility.facility_type, status: "modeled context" },
              geometry: { type: "Point" as const, coordinates: facility.center },
            }))
          : [],
      });
    };
    if (map.isStyleLoaded()) apply(); else map.once("load", apply);
  }, [facilities, layers.infrastructure, layers.intelligence, mapScope]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const visibility = layers.population ? "visible" : "none";
    map.setLayoutProperty("community-context-fill", "visibility", visibility);
    map.setLayoutProperty("community-context-outline", "visibility", visibility);
  }, [layers.population]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const visibility = uncertaintyLens ? "visible" : "none";
    map.setLayoutProperty("uncertainty-fill", "visibility", visibility);
    map.setLayoutProperty("uncertainty-outline", "visibility", visibility);
  }, [uncertaintyLens]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    map.setPaintProperty("osm", "raster-saturation", layers.imagery ? -0.55 : -0.18);
    map.setPaintProperty("osm", "raster-contrast", layers.imagery ? 0.18 : 0.06);
  }, [layers.imagery]);

  // route lines
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource("route-lines") as maplibregl.GeoJSONSource | undefined;
      if (!src) return;
      const features = (route ?? []).map((r) => ({
        type: "Feature" as const,
        properties: { color: exposureColor(r.exposure_level) },
        geometry: r.geometry as GeoJSON.Geometry,
      }));
      src.setData({ type: "FeatureCollection", features });
    };
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [route]);

  // facility markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
    if (!layers.infrastructure || mapScope === "global") return;

    facilities.forEach((f) => {
      const el = document.createElement("button");
      el.type = "button";
      el.setAttribute("aria-label", `${f.name} (${f.facility_type})`);
      el.style.width = "26px";
      el.style.height = "26px";
      el.style.borderRadius = "50%";
      el.style.border = "2px solid white";
      el.style.boxShadow = "0 1px 4px rgba(0,0,0,0.4)";
      el.style.background = facilityColor(f.facility_type);
      el.style.color = "white";
      el.style.fontSize = "11px";
      el.style.fontWeight = "700";
      el.style.display = "flex";
      el.style.alignItems = "center";
      el.style.justifyContent = "center";
      el.style.cursor = "pointer";
      el.textContent = facilityIcon(f.facility_type);
      el.addEventListener("click", () => setPanel({ kind: "place", placeId: f.facility_id }));

      const marker = new maplibregl.Marker({ element: el }).setLngLat(f.center).addTo(map);
      markersRef.current.push(marker);
    });
  }, [facilities, layers.infrastructure, mapScope, setPanel]);

  // fly-to
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyToTarget) return;
    map.flyTo({ center: flyToTarget.center, zoom: flyToTarget.zoom ?? 13, essential: true, duration: 1200 });
  }, [flyToTarget]);

  return (
    <>
      <div ref={containerRef} className="h-full w-full" role="application" aria-label="Interactive EarthPulse map of Lehigh Valley" />
      {mapScope === "local" && <div className="map-model-legend" aria-label="Modeled surface legend">
        <span><i className="legend-rain" /> Rain field</span>
        <span><i className="legend-flood" /> River corridor</span>
        <span><i className="legend-ground" /> Wet slope</span>
        <small>MODELED SURFACES · RESEARCH DEMO</small>
      </div>}
      <div className="sr-only" aria-live="polite">
        {mapScope === "global"
          ? `Global map showing ${globalEvents.length} official GDACS events.`
          : `Regional map showing ${incidents.length} developing incident, ${compoundEvents.flatMap((event) => event.signals).length} compound-hazard signals, ${sensors.length} sensor observations, and ${facilities.length} nearby facilities.`}
        {offsetMinutes > 0 ? ` Forecast impact view at ${offsetMinutes} minutes from now.` : " Current and observed conditions view."}
      </div>
    </>
  );
}

function toHazardFilter(type: string): HazardFilterKey {
  if (type.includes("weather") || type.includes("hurricane") || type.includes("storm")) return "weather";
  if (type.includes("flood")) return "flood";
  if (type.includes("earthquake") || type.includes("tsunami")) return "earthquake";
  if (type.includes("wildfire") || type.includes("fire")) return "wildfire";
  if (type.includes("air") || type.includes("smoke") || type.includes("heat")) return "air";
  return "landslide";
}

function impactForecastGeoJSON(offsetMinutes: number): GeoJSON.FeatureCollection {
  const progress = Math.min(1, Math.max(0.15, offsetMinutes / 720));
  const expand = 0.006 + progress * 0.012;
  const likely = polygonAround([-75.369, 40.621], expand, expand * 0.62);
  const possible = polygonAround([-75.366, 40.621], expand * 1.55, expand * 0.95);
  return {
    type: "FeatureCollection",
    features: [
      { type: "Feature", properties: { band: "possible", certainty: "AI-inferred" }, geometry: possible },
      { type: "Feature", properties: { band: "likely", certainty: "Forecast" }, geometry: likely },
    ],
  };
}

function polygonAround(center: [number, number], x: number, y: number): GeoJSON.Polygon {
  const [lng, lat] = center;
  return { type: "Polygon", coordinates: [[
    [lng - x, lat], [lng - x * 0.55, lat + y], [lng + x * 0.45, lat + y * 0.82],
    [lng + x, lat + y * 0.1], [lng + x * 0.58, lat - y], [lng - x * 0.48, lat - y * 0.78], [lng - x, lat],
  ]] };
}

const LEHIGH_FLOW_PATH: [number, number][] = [
  [-75.424, 40.616], [-75.407, 40.618], [-75.391, 40.6205], [-75.378, 40.6217],
  [-75.366, 40.621], [-75.352, 40.6175], [-75.334, 40.615], [-75.316, 40.612],
];

function compoundSurfaceGeoJSON(
  offsetMinutes: number,
  filters: Record<HazardFilterKey, boolean>,
): GeoJSON.FeatureCollection {
  const future = Math.max(0, Math.min(1, offsetMinutes / 720));
  const features: GeoJSON.Feature[] = [];
  if (filters.weather) {
    features.push({
      type: "Feature",
      properties: { group: "weather", certainty: offsetMinutes > 0 ? "forecast" : "simulated", label: "Modeled rain field" },
      geometry: polygonAround([-75.394 + future * 0.018, 40.632], 0.032 + future * 0.008, 0.017),
    });
  }
  if (filters.flood) {
    const width = 0.0032 + future * 0.0024;
    features.push({
      type: "Feature",
      properties: { group: "flood", certainty: offsetMinutes > 0 ? "forecast" : "simulated", label: "Modeled river corridor" },
      geometry: riverCorridorPolygon(width),
    });
  }
  if (filters.landslide) {
    features.push({
      type: "Feature",
      properties: { group: "landslide", certainty: "simulated", label: "Wet-slope context" },
      geometry: polygonAround([-75.389, 40.6105], 0.015, 0.0065),
    });
  }
  return { type: "FeatureCollection", features };
}

function riverCorridorPolygon(width: number): GeoJSON.Polygon {
  const upper = LEHIGH_FLOW_PATH.map(([lng, lat], index) => [lng, lat + width * (index % 2 ? 0.8 : 1)]);
  const lower = [...LEHIGH_FLOW_PATH].reverse().map(([lng, lat], index) => [lng, lat - width * (index % 2 ? 0.9 : 0.7)]);
  return { type: "Polygon", coordinates: [[...upper, ...lower, upper[0]]] };
}

function flowParticlesGeoJSON(phase: number, offsetMinutes: number): GeoJSON.FeatureCollection {
  const speedHint = 0.65 + Math.max(0, Math.min(0.35, offsetMinutes / 1440));
  const features = Array.from({ length: 12 }, (_, index) => {
    const progress = (phase * speedHint + index / 12) % 1;
    const scaled = progress * (LEHIGH_FLOW_PATH.length - 1);
    const segment = Math.min(LEHIGH_FLOW_PATH.length - 2, Math.floor(scaled));
    const local = scaled - segment;
    const start = LEHIGH_FLOW_PATH[segment];
    const end = LEHIGH_FLOW_PATH[segment + 1];
    return {
      type: "Feature" as const,
      properties: { phase: (index % 4) / 3, meaning: "directional illustration" },
      geometry: {
        type: "Point" as const,
        coordinates: [start[0] + (end[0] - start[0]) * local, start[1] + (end[1] - start[1]) * local],
      },
    };
  });
  return { type: "FeatureCollection", features };
}

function uncertaintyGeoJSON(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [
    { type: "Feature", properties: { reason: "Road elevation is estimated" }, geometry: polygonAround([-75.392, 40.615], 0.014, 0.009) },
    { type: "Feature", properties: { reason: "Sparse gauge coverage" }, geometry: polygonAround([-75.343, 40.638], 0.018, 0.011) },
  ] };
}

function communityContextGeoJSON(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [
    { type: "Feature", properties: { label: "Community exposure context" }, geometry: polygonAround([-75.382, 40.616], 0.02, 0.012) },
  ] };
}
