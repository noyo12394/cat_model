import type { Map as MapLibreMap, StyleSpecification } from "maplibre-gl";

const OPENFREEMAP_DARK = "https://tiles.openfreemap.org/styles/dark";
const OPENFREEMAP_LIGHT = "https://tiles.openfreemap.org/styles/positron";

/**
 * Return a public MapLibre style that works without a credential.
 *
 * MapTiler remains an opt-in upgrade for teams that have a valid,
 * referrer-restricted browser key. Merely having an old key in the deployment
 * environment no longer selects it, which prevents provider watermarks from
 * replacing the map when a key expires or is misconfigured.
 */
export function basemapStyle(dark: boolean, preferSatellite = false): string {
  const mapTilerKey = process.env.NEXT_PUBLIC_MAPTILER_KEY;
  const useMapTiler = process.env.NEXT_PUBLIC_MAP_PROVIDER === "maptiler" && Boolean(mapTilerKey);
  if (useMapTiler) {
    const style = preferSatellite ? "hybrid" : dark ? "dataviz-dark" : "dataviz";
    return `https://api.maptiler.com/maps/${style}/style.json?key=${encodeURIComponent(mapTilerKey!)}`;
  }
  return dark ? OPENFREEMAP_DARK : OPENFREEMAP_LIGHT;
}

export const historicBasemapStyle: StyleSpecification | string = OPENFREEMAP_DARK;

/** Some community styles reference optional sprite glyphs. Missing decoration
 * must not produce console noise or block the data layers used by RiskChain. */
export function installMissingStyleImageFallback(map: MapLibreMap) {
  map.on("styleimagemissing", (event) => {
    if (map.hasImage(event.id)) return;
    map.addImage(event.id, { width: 1, height: 1, data: new Uint8Array([0, 0, 0, 0]) });
  });
}
