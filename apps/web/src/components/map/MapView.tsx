"use client";

import dynamic from "next/dynamic";
import type { RouteOption } from "@/lib/types";

const MapLibreView = dynamic(() => import("./MapLibreView").then((m) => m.MapLibreView), { ssr: false });
const GoogleMapView = dynamic(() => import("./GoogleMapView").then((m) => m.GoogleMapView), { ssr: false });

/** Chooses the map engine (section 7 / section 46): MapLibre + OpenStreetMap
 * needs no API key and is the default, so the product works out of the box.
 * Setting NEXT_PUBLIC_GOOGLE_MAPS_API_KEY upgrades to Google Maps Platform. */
export function MapView({ route }: { route?: RouteOption[] }) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  if (apiKey) {
    return <GoogleMapView apiKey={apiKey} route={route} />;
  }
  return <MapLibreView route={route} />;
}
