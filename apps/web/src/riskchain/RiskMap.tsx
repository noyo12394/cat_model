"use client";

import { useEffect, useRef } from "react";
import type { GlobalEvent, ModelResultLayer } from "@/lib/types";

type Selection = {
  id: string;
  title: string;
  subtitle: string;
  status: "Observed" | "Officially reported" | "Demo" | "Geocoded location";
  source: string;
  center: [number, number];
  zoom?: number;
};

type Props = {
  events: GlobalEvent[];
  scope: "global" | "local";
  operationsMode: boolean;
  hazard: string;
  focus?: [number, number] | null;
  focusZoom?: number | null;
  modelLayer?: ModelResultLayer | null;
  onSelect: (selection: Selection) => void;
};

declare global {
  interface Window {
    google?: typeof google;
    __riskChainGoogleReady?: () => void;
  }
}

let googleLoader: Promise<void> | null = null;

function loadGoogle(apiKey: string) {
  if (window.google?.maps) return Promise.resolve();
  if (googleLoader) return googleLoader;
  googleLoader = new Promise<void>((resolve, reject) => {
    window.__riskChainGoogleReady = resolve;
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&callback=__riskChainGoogleReady&v=weekly`;
    script.async = true;
    script.onerror = () => reject(new Error("Google Maps failed to load"));
    document.head.appendChild(script);
  });
  return googleLoader;
}

function eventColor(event: GlobalEvent) {
  if (event.alert_level === "red") return "#d93025";
  if (event.alert_level === "orange") return "#f29900";
  const hazard = event.event_type.toLowerCase();
  if (hazard === "eq" || hazard.includes("earth")) return "#7e57c2";
  if (hazard === "wf" || hazard.includes("fire")) return "#f4511e";
  if (hazard === "fl" || hazard.includes("flood")) return "#1a73e8";
  return "#188038";
}

function damageColor(value: number) {
  if (value >= 0.45) return "#d93025";
  if (value >= 0.25) return "#f4511e";
  if (value >= 0.1) return "#f9ab00";
  if (value > 0) return "#1a73e8";
  return "#8aa0ae";
}

export function RiskMap({ events, scope, operationsMode, hazard, focus, focusZoom, modelLayer, onSelect }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const onSelectRef = useRef(onSelect);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    let active = true;
    let mapLibre: import("maplibre-gl").Map | undefined;
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    const container = ref.current;

    async function start() {
      if (!container) return;
      if (apiKey) {
        try {
          await loadGoogle(apiKey);
          if (!active || !window.google) return;
          const googleCenter = focus ? { lat: focus[1], lng: focus[0] } : scope === "global" ? { lat: 18, lng: 5 } : { lat: 40.6259, lng: -75.3705 };
          const map = new google.maps.Map(container, {
            center: googleCenter,
            zoom: focus ? (focusZoom ?? 12) : scope === "global" ? 2 : 13,
            mapId: process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID",
            streetViewControl: false,
            mapTypeControl: false,
            fullscreenControl: false,
            gestureHandling: "greedy",
          });
          events.slice(0, 160).forEach((event) => {
            const marker = new google.maps.Marker({
              map,
              position: { lat: event.center[1], lng: event.center[0] },
              title: event.name,
              icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: event.alert_level === "red" ? 9 : event.alert_level === "orange" ? 7 : 5,
                fillColor: eventColor(event),
                fillOpacity: 0.92,
                strokeColor: "#ffffff",
                strokeWeight: 2,
              },
            });
            marker.addListener("click", () => onSelectRef.current({
              id: event.event_id,
              title: event.name,
              subtitle: `${event.event_type} · ${event.country}`,
              status: "Officially reported",
              source: event.source,
              center: event.center,
              zoom: 7,
            }));
          });
          if (scope === "local") {
            new google.maps.Data({ map }).addGeoJson({
              type: "Feature",
              properties: { status: "demo" },
              geometry: { type: "Polygon", coordinates: [[[-75.395, 40.612], [-75.35, 40.612], [-75.344, 40.64], [-75.393, 40.642], [-75.395, 40.612]]] },
            });
            modelLayer?.geojson.features.forEach((feature) => {
              const value = feature.properties.value;
              const marker = new google.maps.Marker({
                map,
                position: { lat: feature.geometry.coordinates[1], lng: feature.geometry.coordinates[0] },
                title: `${feature.properties.name}: ${(value * 100).toFixed(1)}% mean damage ratio (modelled demo)`,
                icon: {
                  path: google.maps.SymbolPath.SQUARE,
                  scale: 8,
                  fillColor: damageColor(value),
                  fillOpacity: 0.9,
                  strokeColor: "#ffffff",
                  strokeWeight: 1.5,
                },
              });
              marker.addListener("click", () => onSelectRef.current({
                id: feature.properties.asset_id,
                title: feature.properties.name,
                subtitle: `${(value * 100).toFixed(1)}% modelled mean damage · ${feature.properties.occupancy}`,
                status: "Demo",
                source: "RiskChain immutable flood-model result",
                center: feature.geometry.coordinates,
                zoom: 15,
              }));
            });
          }
          return;
        } catch {
          // A failed optional provider falls through to the open map engine.
        }
      }

      const maplibregl = (await import("maplibre-gl")).default;
      if (!active) return;
      mapLibre = new maplibregl.Map({
        container,
        style: operationsMode
          ? "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
          : "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        center: focus ?? (scope === "global" ? [5, 18] : [-75.3705, 40.6259]),
        zoom: focus ? (focusZoom ?? 12) : scope === "global" ? 1.75 : 12.4,
        attributionControl: false,
      });
      mapLibre.addControl(new maplibregl.NavigationControl({ showCompass: true }), "bottom-right");
      mapLibre.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
      mapLibre.on("load", () => {
        if (!mapLibre) return;
        if (scope === "local" && hazard === "flood") {
          mapLibre.addSource("demo-flood", {
            type: "geojson",
            data: { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[-75.395, 40.612], [-75.35, 40.612], [-75.344, 40.64], [-75.393, 40.642], [-75.395, 40.612]]] } },
          });
          mapLibre.addLayer({ id: "demo-flood-fill", type: "fill", source: "demo-flood", paint: { "fill-color": "#1a73e8", "fill-opacity": 0.2 } });
          mapLibre.addLayer({ id: "demo-flood-line", type: "line", source: "demo-flood", paint: { "line-color": "#1a73e8", "line-width": 2, "line-dasharray": [2, 2] } });
        }
        const visible = scope === "global" ? events.slice(0, 160) : [];
        visible.forEach((event) => {
          const node = document.createElement("button");
          node.className = "map-event-marker";
          node.style.setProperty("--marker-color", eventColor(event));
          node.title = `${event.name} — ${event.alert_level} alert`;
          node.setAttribute("aria-label", node.title);
          node.onclick = () => onSelectRef.current({ id: event.event_id, title: event.name, subtitle: `${event.event_type} · ${event.country}`, status: "Officially reported", source: event.source, center: event.center, zoom: 7 });
          new maplibregl.Marker({ element: node }).setLngLat(event.center).addTo(mapLibre!);
        });
        if (scope === "local") {
          const node = document.createElement("button");
          node.className = "map-event-marker local-pin";
          node.style.setProperty("--marker-color", "#1a73e8");
          node.title = "Bethlehem flood demonstration";
          node.onclick = () => onSelectRef.current({ id: "bethlehem-demo", title: "Bethlehem flood demonstration", subtitle: "100-year flood scenario · Lehigh Valley", status: "Demo", source: "RiskChain approved demonstration engine", center: [-75.3705, 40.6259] });
          new maplibregl.Marker({ element: node }).setLngLat([-75.3705, 40.6259]).addTo(mapLibre);
          modelLayer?.geojson.features.forEach((feature) => {
            const value = feature.properties.value;
            const assetNode = document.createElement("button");
            assetNode.className = "map-model-asset";
            assetNode.style.setProperty("--asset-color", damageColor(value));
            assetNode.title = `${feature.properties.name}: ${(value * 100).toFixed(1)}% mean damage ratio (modelled demo)`;
            assetNode.setAttribute("aria-label", assetNode.title);
            assetNode.onclick = () => onSelectRef.current({
              id: feature.properties.asset_id,
              title: feature.properties.name,
              subtitle: `${(value * 100).toFixed(1)}% modelled mean damage · ${feature.properties.occupancy}`,
              status: "Demo",
              source: "RiskChain immutable flood-model result",
              center: feature.geometry.coordinates,
              zoom: 15,
            });
            new maplibregl.Marker({ element: assetNode }).setLngLat(feature.geometry.coordinates).addTo(mapLibre!);
          });
        }
      });
    }
    void start();
    return () => {
      active = false;
      mapLibre?.remove();
      container?.replaceChildren();
    };
  }, [events, focus, focusZoom, hazard, modelLayer, operationsMode, scope]);

  return <div ref={ref} className="risk-map" role="application" aria-label="Interactive catastrophe risk map" />;
}

export type { Selection as MapSelection };
