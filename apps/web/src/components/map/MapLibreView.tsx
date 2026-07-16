"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useAppStore } from "@/lib/store";
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
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export function MapLibreView({ route }: { route?: RouteOption[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const { facilities, incidents } = useMapData();
  const flyToTarget = useAppStore((s) => s.flyToTarget);
  const layers = useAppStore((s) => s.layers);
  const setPanel = useAppStore((s) => s.setPanel);

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

      map.addSource("route-lines", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "route-lines-layer",
        type: "line",
        source: "route-lines",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": ["get", "color"], "line-width": 5, "line-opacity": 0.85 },
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // incident geometry (official-alert style: solid, strong outline)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource("incident-geometry") as maplibregl.GeoJSONSource | undefined;
      if (!src) return;
      const features = layers.hazards
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
  }, [incidents, layers.hazards]);

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
    if (!layers.infrastructure) return;

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
  }, [facilities, layers.infrastructure, setPanel]);

  // fly-to
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyToTarget) return;
    map.flyTo({ center: flyToTarget.center, zoom: flyToTarget.zoom ?? 13, essential: true, duration: 1200 });
  }, [flyToTarget]);

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="EarthPulse map" />;
}
