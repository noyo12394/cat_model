import campFire from "../../data/historic/camp-fire-2018.json";
import harvey from "../../data/historic/hurricane-harvey-2017.json";
import katrina from "../../data/historic/hurricane-katrina-2005.json";
import tornadoes from "../../data/historic/kentucky-tornado-outbreak-2021.json";
import northridge from "../../data/historic/northridge-1994.json";

export type HistoricSource = {
  id: string; name: string; url: string; retrieved_at: string; license: string; panels: string[];
};

export type HistoricDataset = {
  slug: string; name: string; provenance: "observed" | "officially reported" | "modelled" | "demo";
  resolution: string; vintage: string; source_id: string; unit: string; denominator: string;
  geometry_status: "reference_only" | "not_available";
};

export type HistoricReference = {
  label: string; source_id: string; status: "reference_only" | "not_available";
};

export type HistoricReading = {
  title: string; url: string; source_id: string;
};

export type HistoricLoss = {
  display: string; currency: string; loss_year: number; inflation_basis: string; source_ids: string[];
};

export type HistoricEvent = {
  slug: string; name: string; hazard: string; hazard_code: string; country: "USA"; region: string;
  start_date: string; end_date: string; center: [number, number]; center_label: string; center_source_id: string;
  map_zoom: number; footprint_geometry_reference: HistoricReference; headline_loss: string;
  insured_loss: HistoricLoss; economic_loss: HistoricLoss; datasets: HistoricDataset[];
  related_reading: HistoricReading[]; sources: HistoricSource[];
};

export type HistoricAction = "view" | "download" | "read";

export const HISTORIC_ACTIONS: ReadonlyArray<{ value: HistoricAction; label: string; description: string }> = [
  { value: "view", label: "View on map", description: "Render the source point and the selected dataset availability on the event map." },
  { value: "download", label: "Download data", description: "Build a ZIP evidence bundle with GeoJSON, CSV metadata, and sources.json." },
  { value: "read", label: "Read more", description: "Open curated links to the authoritative event and dataset pages." },
];

export const HISTORIC_EVENTS = [katrina, northridge, campFire, harvey, tornadoes] as unknown as HistoricEvent[];

export function historicEvent(slug: string) {
  return HISTORIC_EVENTS.find((event) => event.slug === slug);
}

export function historicDataset(event: HistoricEvent, slug: string) {
  return event.datasets.find((dataset) => dataset.slug === slug);
}

export function historicAction(value: string | string[] | undefined): HistoricAction | undefined {
  if (typeof value !== "string") return undefined;
  return HISTORIC_ACTIONS.some((action) => action.value === value) ? value as HistoricAction : undefined;
}

export function pipelineFor(event: HistoricEvent, dataset: HistoricDataset) {
  const source = event.sources.find((item) => item.id === dataset.source_id);
  return [
    { step: 1, label: "Resolve curated event", detail: `${event.slug} → ${event.name}; dates ${event.start_date} to ${event.end_date}.`, units: "ISO date / WGS84 point" },
    { step: 2, label: "Open authoritative dataset", detail: source?.url ?? "No resolvable source URL is available.", units: dataset.unit },
    { step: 3, label: "Select dataset", detail: `${dataset.name}; vintage ${dataset.vintage}; resolution ${dataset.resolution}.`, units: dataset.unit },
    { step: 4, label: "Apply transformations", detail: "Preserve source units and provenance; do not interpolate missing geometry or loss values.", units: dataset.unit },
    { step: 5, label: "Render and package", detail: `Map the cited reference point and expose the ${dataset.geometry_status.replaceAll("_", " ")} geometry state; package GeoJSON, CSV metadata, README, and sources.json in one ZIP.`, units: dataset.denominator },
  ];
}
