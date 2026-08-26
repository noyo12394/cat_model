import campFire from "../../data/historic/camp-fire-2018.json";
import harvey from "../../data/historic/hurricane-harvey-2017.json";
import ian from "../../data/historic/hurricane-ian-2022.json";
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

export type HistoricLoss = {
  display: string; currency: string; loss_year: number; inflation_basis: string; source_ids: string[];
};

export type HistoricEvent = {
  slug: string; name: string; hazard: string; hazard_code: string; country: "USA"; region: string;
  start_date: string; end_date: string; center: [number, number]; headline_loss: string;
  insured_loss: HistoricLoss; economic_loss: HistoricLoss; datasets: HistoricDataset[]; sources: HistoricSource[];
};

export const HISTORIC_EVENTS = [northridge, ian, harvey, campFire, tornadoes] as unknown as HistoricEvent[];

export function historicEvent(slug: string) {
  return HISTORIC_EVENTS.find((event) => event.slug === slug);
}

export function historicDataset(event: HistoricEvent, slug: string) {
  return event.datasets.find((dataset) => dataset.slug === slug);
}

export function pipelineFor(event: HistoricEvent, dataset: HistoricDataset) {
  const source = event.sources.find((item) => item.id === dataset.source_id);
  return [
    { step: 1, label: "Resolve curated event", detail: `${event.slug} → ${event.name}; dates ${event.start_date} to ${event.end_date}.`, units: "ISO date / WGS84 point" },
    { step: 2, label: "Open authoritative dataset", detail: source?.url ?? "No resolvable source URL is available.", units: dataset.unit },
    { step: 3, label: "Select dataset", detail: `${dataset.name}; vintage ${dataset.vintage}; resolution ${dataset.resolution}.`, units: dataset.unit },
    { step: 4, label: "Apply transformations", detail: "Preserve source units and provenance; do not interpolate missing geometry or loss values.", units: dataset.unit },
    { step: 5, label: "Render and package", detail: `Map the official origin point and expose the ${dataset.geometry_status.replaceAll("_", " ")} geometry state; package CSV plus sources manifest.`, units: dataset.denominator },
  ];
}
