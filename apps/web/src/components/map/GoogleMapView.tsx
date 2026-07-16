"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/lib/store";
import { useMapData } from "./useMapData";
import { facilityColor } from "./facilityStyle";
import type { RouteOption } from "@/lib/types";
import { exposureColor } from "./facilityStyle";

const BETHLEHEM_CENTER = { lat: 40.6259, lng: -75.3705 };

declare global {
  interface Window {
    google?: typeof google;
    __earthpulseGoogleMapsCallback?: () => void;
  }
}

let scriptLoadingPromise: Promise<void> | null = null;

function loadGoogleMaps(apiKey: string): Promise<void> {
  if (window.google?.maps) return Promise.resolve();
  if (scriptLoadingPromise) return scriptLoadingPromise;
  scriptLoadingPromise = new Promise((resolve, reject) => {
    window.__earthpulseGoogleMapsCallback = () => resolve();
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=__earthpulseGoogleMapsCallback&v=weekly`;
    script.async = true;
    script.onerror = () => reject(new Error("Failed to load Google Maps JavaScript API"));
    document.head.appendChild(script);
  });
  return scriptLoadingPromise;
}

/** Google Maps Platform engine (section 7). Only mounted when
 * NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is configured - see MapView.tsx. Uses a
 * browser-restricted key; Route/Places calls still go through the backend
 * proxy per section 44, this component only renders the base map + our own
 * overlays via the Maps JS API's Data layer and Marker/Polyline classes. */
export function GoogleMapView({ apiKey, route }: { apiKey: string; route?: RouteOption[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const polylinesRef = useRef<google.maps.Polyline[]>([]);
  const dataLayerRef = useRef<google.maps.Data | null>(null);
  const { facilities, incidents } = useMapData();
  const flyToTarget = useAppStore((s) => s.flyToTarget);
  const layers = useAppStore((s) => s.layers);
  const setPanel = useAppStore((s) => s.setPanel);

  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps(apiKey).then(() => {
      if (cancelled || !containerRef.current || mapRef.current) return;
      const map = new google.maps.Map(containerRef.current, {
        center: BETHLEHEM_CENTER,
        zoom: 12,
        mapId: "EARTHPULSE_DEMO",
        streetViewControl: true,
        fullscreenControl: false,
      });
      mapRef.current = map;
      dataLayerRef.current = new google.maps.Data({ map });
      dataLayerRef.current.setStyle({
        fillColor: "#d13b3b",
        fillOpacity: 0.15,
        strokeColor: "#d13b3b",
        strokeWeight: 3,
      });
    });
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  useEffect(() => {
    const map = mapRef.current;
    const dataLayer = dataLayerRef.current;
    if (!map || !dataLayer) return;
    dataLayer.forEach((f) => dataLayer.remove(f));
    if (!layers.hazards) return;
    incidents
      .filter((inc) => inc.geometry?.type === "Polygon")
      .forEach((inc) => {
        const coords = (inc.geometry as { coordinates: [number, number][][] }).coordinates[0];
        dataLayer.addGeoJson({
          type: "Feature",
          properties: { title: inc.title },
          geometry: { type: "Polygon", coordinates: [coords] },
        });
      });
  }, [incidents, layers.hazards]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];
    if (!layers.infrastructure) return;
    facilities.forEach((f) => {
      const marker = new google.maps.Marker({
        position: { lat: f.center[1], lng: f.center[0] },
        map,
        title: f.name,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: facilityColor(f.facility_type),
          fillOpacity: 1,
          strokeColor: "white",
          strokeWeight: 2,
        },
      });
      marker.addListener("click", () => setPanel({ kind: "place", placeId: f.facility_id }));
      markersRef.current.push(marker);
    });
  }, [facilities, layers.infrastructure, setPanel]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    polylinesRef.current.forEach((p) => p.setMap(null));
    polylinesRef.current = [];
    (route ?? []).forEach((r) => {
      if (r.geometry.type !== "LineString") return;
      const path = r.geometry.coordinates.map(([lng, lat]) => ({ lat, lng }));
      const line = new google.maps.Polyline({
        path,
        map,
        strokeColor: exposureColor(r.exposure_level),
        strokeWeight: 5,
        strokeOpacity: 0.85,
      });
      polylinesRef.current.push(line);
    });
  }, [route]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyToTarget) return;
    map.panTo({ lat: flyToTarget.center[1], lng: flyToTarget.center[0] });
    map.setZoom(flyToTarget.zoom ?? 13);
  }, [flyToTarget]);

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="EarthPulse map (Google Maps)" />;
}
