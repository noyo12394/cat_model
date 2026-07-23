export type GenomeHazard = "earthquake" | "cyclone" | "flood" | "wildfire" | "volcano";
export type GenomeEra = "pre_2000" | "2000s" | "2010s" | "2020s";
export type GenomeSetting = "coastal" | "inland" | "island" | "mountain";
export type GenomeOnset = "rapid" | "multi_day" | "seasonal";
export type GenomeDriver = "ground" | "wind" | "water" | "thermal" | "ash";
export type GenomeSecondary = "tsunami" | "surge" | "landslide" | "smoke" | "lahar";
export type GenomeSourceFamily = "usgs" | "noaa" | "official_other";

export type GenomeTrait = {
  id: string;
  label: string;
  group: "Hazard" | "Era" | "Setting" | "Onset" | "Driver" | "Secondary" | "Archive";
};

export type HistoricalGenomeEvent = {
  id: string;
  name: string;
  year: number;
  dateLabel: string;
  country: string;
  center: [number, number];
  hazard: GenomeHazard;
  setting: GenomeSetting;
  onset: GenomeOnset;
  drivers: GenomeDriver[];
  secondary: GenomeSecondary[];
  sourceFamily: GenomeSourceFamily;
  sourceLabel: string;
  sourceUrl: string;
  coordinateNote: string;
  summary: string;
};

export type ArchiveSource = {
  id: string;
  name: string;
  provider: string;
  hazardScope: string;
  coverage: string;
  access: string;
  updateCadence: string;
  integration: "search" | "external";
  limitation: string;
  url: string;
};

// These traits are deliberately a categorical metadata ontology. They are not
// intensity measures, physical hazard parameters, damage ratios, likelihoods,
// or loss-model inputs. The vector is used only for transparent catalogue
// navigation in the Genome Lab.
export const GENOME_TRAITS: GenomeTrait[] = [
  { id: "hazard_earthquake", label: "Earthquake", group: "Hazard" },
  { id: "hazard_cyclone", label: "Tropical cyclone", group: "Hazard" },
  { id: "hazard_flood", label: "Flood", group: "Hazard" },
  { id: "hazard_wildfire", label: "Wildfire", group: "Hazard" },
  { id: "hazard_volcano", label: "Volcano", group: "Hazard" },
  { id: "era_pre_2000", label: "Before 2000", group: "Era" },
  { id: "era_2000s", label: "2000–2009", group: "Era" },
  { id: "era_2010s", label: "2010–2019", group: "Era" },
  { id: "era_2020s", label: "2020 onward", group: "Era" },
  { id: "setting_coastal", label: "Coastal setting", group: "Setting" },
  { id: "setting_inland", label: "Inland setting", group: "Setting" },
  { id: "setting_island", label: "Island setting", group: "Setting" },
  { id: "setting_mountain", label: "Mountain setting", group: "Setting" },
  { id: "onset_rapid", label: "Rapid onset", group: "Onset" },
  { id: "onset_multi_day", label: "Multi-day onset", group: "Onset" },
  { id: "onset_seasonal", label: "Seasonal / prolonged", group: "Onset" },
  { id: "driver_ground", label: "Ground motion", group: "Driver" },
  { id: "driver_wind", label: "Wind", group: "Driver" },
  { id: "driver_water", label: "Water", group: "Driver" },
  { id: "driver_thermal", label: "Thermal / fire", group: "Driver" },
  { id: "driver_ash", label: "Ash / volcanic material", group: "Driver" },
  { id: "secondary_tsunami", label: "Tsunami context", group: "Secondary" },
  { id: "secondary_surge", label: "Storm-surge context", group: "Secondary" },
  { id: "secondary_landslide", label: "Landslide context", group: "Secondary" },
  { id: "secondary_smoke", label: "Smoke context", group: "Secondary" },
  { id: "secondary_lahar", label: "Lahar context", group: "Secondary" },
  { id: "secondary_compound", label: "Multiple secondary contexts", group: "Secondary" },
  { id: "archive_usgs", label: "USGS archive family", group: "Archive" },
  { id: "archive_noaa", label: "NOAA archive family", group: "Archive" },
  { id: "archive_official_other", label: "Other official archive", group: "Archive" },
];

const SOURCES = {
  usgs: {
    label: "USGS significant-earthquake archive",
    url: "https://earthquake.usgs.gov/earthquakes/browse/significant.php",
  },
  noaaCyclone: {
    label: "NOAA National Hurricane Center tropical cyclone reports",
    url: "https://www.nhc.noaa.gov/data/tcr/",
  },
  noaaClimate: {
    label: "NOAA National Centers for Environmental Information",
    url: "https://www.ncei.noaa.gov/",
  },
  officialFire: {
    label: "Official wildfire information archive",
    url: "https://www.nifc.gov/fire-information/statistics",
  },
  officialVolcano: {
    label: "USGS Volcano Hazards Program",
    url: "https://www.usgs.gov/programs/VHP",
  },
} as const;

// A catastrophe archive is federated: no one public database consistently
// captures every hazard, geography, time period, footprint, or loss. These
// cards identify the authoritative catalogue currently available for each
// supported source family. Only the USGS catalogue is queried in-app today;
// the other archives remain explicitly external until their data licence,
// update process, and source-to-schema mapping are approved.
export const ARCHIVE_SOURCES: ArchiveSource[] = [
  {
    id: "usgs-earthquakes",
    name: "USGS Earthquake Catalog",
    provider: "U.S. Geological Survey",
    hazardScope: "Global earthquakes",
    coverage: "Custom time, magnitude, and geographic queries; source responses are paginated.",
    access: "Live GeoJSON query in RiskChain",
    updateCadence: "Source-managed; live and historical query service",
    integration: "search",
    limitation: "An earthquake record is not a shaking footprint, damage observation, or CAT loss result.",
    url: "https://earthquake.usgs.gov/fdsnws/event/1/",
  },
  {
    id: "noaa-ibtracs",
    name: "IBTrACS tropical cyclone archive",
    provider: "NOAA National Centers for Environmental Information",
    hazardScope: "Global tropical cyclones",
    coverage: "1848–present, global best-track records from official warning centres.",
    access: "Official download and map tools (CSV, shapefile, netCDF, WMS)",
    updateCadence: "Annual archive update",
    integration: "external",
    limitation: "Best-track positions and winds are not a local wind-field, surge model, or insured-loss dataset.",
    url: "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00834",
  },
  {
    id: "noaa-storm-events",
    name: "NOAA Storm Events Database",
    provider: "NOAA National Centers for Environmental Information",
    hazardScope: "United States weather and climate events",
    coverage: "U.S. events from 1950 onward, distributed as source bulk files.",
    access: "Official bulk archive",
    updateCadence: "Source-managed archive releases",
    integration: "external",
    limitation: "U.S. coverage only; source reports require event-specific interpretation and are not a loss model.",
    url: "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/",
  },
  {
    id: "smithsonian-volcano",
    name: "Global Volcanism Program",
    provider: "Smithsonian Institution",
    hazardScope: "Volcanoes and documented eruptive activity",
    coverage: "Global volcano reference information and eruption reporting.",
    access: "Official catalogue and reports",
    updateCadence: "Source-managed",
    integration: "external",
    limitation: "Volcanic reference records do not supply a local ashfall, lahar, or damage footprint by default.",
    url: "https://volcano.si.edu/",
  },
];

// The 30 records below are a source-linked, editorially curated catalogue of
// documented catastrophes. Their displayed coordinate is a reference point for
// atlas navigation, never an event extent, fault plane, wind field, perimeter,
// flood footprint, or damage footprint.
export const HISTORICAL_GENOME_EVENTS: HistoricalGenomeEvent[] = [
  { id: "san-francisco-1906", name: "San Francisco earthquake", year: 1906, dateLabel: "1906", country: "United States", center: [-122.42, 37.77], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: [], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference San Francisco location; not a rupture, shaking, fire, or loss footprint.", summary: "A documented earthquake represented by a city reference location for catalogue navigation." },
  { id: "kanto-1923", name: "Great Kantō earthquake", year: 1923, dateLabel: "1923", country: "Japan", center: [139.6, 35.2], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: [], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference Kantō-region location; not a rupture, shaking, fire, or loss footprint.", summary: "A documented historical earthquake included as a source-linked metadata record." },
  { id: "guatemala-1976", name: "Guatemala earthquake", year: 1976, dateLabel: "1976", country: "Guatemala", center: [-89.1, 15.3], hazard: "earthquake", setting: "inland", onset: "rapid", drivers: ["ground"], secondary: ["landslide"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral region; not a shaking or impact footprint.", summary: "A documented earthquake in the source-linked historical catalogue." },
  { id: "mount-st-helens-1980", name: "Mount St. Helens eruption", year: 1980, dateLabel: "1980", country: "United States", center: [-122.18, 46.2], hazard: "volcano", setting: "mountain", onset: "rapid", drivers: ["ash"], secondary: ["lahar", "landslide"], sourceFamily: "official_other", sourceLabel: SOURCES.officialVolcano.label, sourceUrl: SOURCES.officialVolcano.url, coordinateNote: "Reference volcano location; not an ashfall, blast, lahar, or exclusion-zone footprint.", summary: "A documented volcanic eruption represented by a reference location and categorical context." },
  { id: "bangladesh-flood-1988", name: "Bangladesh floods", year: 1988, dateLabel: "1988", country: "Bangladesh", center: [90.4, 23.8], hazard: "flood", setting: "inland", onset: "seasonal", drivers: ["water"], secondary: [], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference central Bangladesh location; not an inundation or depth footprint.", summary: "A documented flood season used only for source-linked metadata comparison." },
  { id: "nargis-2008", name: "Cyclone Nargis", year: 2008, dateLabel: "2008", country: "Myanmar", center: [96.1, 16.0], hazard: "cyclone", setting: "coastal", onset: "multi_day", drivers: ["wind", "water"], secondary: ["surge"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference Myanmar coastal location; not a storm track, wind field, surge, or loss footprint.", summary: "A documented cyclone represented for metadata navigation, not historical hazard reconstruction." },
  { id: "valdivia-1960", name: "Valdivia earthquake", year: 1960, dateLabel: "1960", country: "Chile", center: [-73.05, -38.24], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: ["tsunami", "landslide"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference location in southern Chile; not a rupture footprint.", summary: "A documented great earthquake used here only as a historical metadata reference." },
  { id: "alaska-1964", name: "Alaska earthquake", year: 1964, dateLabel: "1964", country: "United States", center: [-147.65, 61.02], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: ["tsunami", "landslide"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference location in south-central Alaska; not a rupture footprint.", summary: "A documented Alaska earthquake selected for the source-linked historical catalogue." },
  { id: "tangshan-1976", name: "Tangshan earthquake", year: 1976, dateLabel: "1976", country: "China", center: [118.18, 39.63], hazard: "earthquake", setting: "inland", onset: "rapid", drivers: ["ground"], secondary: [], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference location near Tangshan; not an impact boundary.", summary: "A documented inland earthquake in the historical metadata catalogue." },
  { id: "michoacan-1985", name: "Michoacán earthquake", year: 1985, dateLabel: "1985", country: "Mexico", center: [-102.53, 18.19], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: [], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral area; not a shaking or loss footprint.", summary: "A documented earthquake included to compare source-context traits, not loss outcomes." },
  { id: "kobe-1995", name: "Kobe earthquake", year: 1995, dateLabel: "1995", country: "Japan", center: [135.03, 34.59], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: [], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral area; not a damage footprint.", summary: "A documented urban earthquake used as a catalogue reference." },
  { id: "sumatra-2004", name: "Sumatra–Andaman earthquake", year: 2004, dateLabel: "2004", country: "Indonesia", center: [95.85, 3.32], hazard: "earthquake", setting: "island", onset: "rapid", drivers: ["ground"], secondary: ["tsunami"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral area; not a rupture or tsunami footprint.", summary: "A documented subduction-zone event with tsunami context explicitly encoded as metadata." },
  { id: "haiti-2010", name: "Haiti earthquake", year: 2010, dateLabel: "2010", country: "Haiti", center: [-72.53, 18.46], hazard: "earthquake", setting: "island", onset: "rapid", drivers: ["ground"], secondary: ["landslide"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral area; not an intensity footprint.", summary: "A documented earthquake selected for the historical catalogue." },
  { id: "tohoku-2011", name: "Tōhoku earthquake", year: 2011, dateLabel: "2011", country: "Japan", center: [142.37, 38.3], hazard: "earthquake", setting: "coastal", onset: "rapid", drivers: ["ground"], secondary: ["tsunami"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference offshore epicentral area; not a tsunami footprint.", summary: "A documented earthquake with tsunami context retained as a categorical trait only." },
  { id: "gorkha-2015", name: "Gorkha earthquake", year: 2015, dateLabel: "2015", country: "Nepal", center: [84.71, 28.15], hazard: "earthquake", setting: "mountain", onset: "rapid", drivers: ["ground"], secondary: ["landslide"], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral area; not a shaking footprint.", summary: "A documented mountain-region earthquake in the curated catalogue." },
  { id: "turkiye-2023", name: "Kahramanmaraş earthquakes", year: 2023, dateLabel: "2023", country: "Türkiye", center: [37.03, 37.17], hazard: "earthquake", setting: "inland", onset: "rapid", drivers: ["ground"], secondary: [], sourceFamily: "usgs", sourceLabel: SOURCES.usgs.label, sourceUrl: SOURCES.usgs.url, coordinateNote: "Reference epicentral area; not a rupture or loss footprint.", summary: "A documented earthquake sequence represented by one reference location for atlas navigation." },
  { id: "bhola-1970", name: "Bhola cyclone", year: 1970, dateLabel: "1970", country: "Bangladesh", center: [90.5, 22.1], hazard: "cyclone", setting: "coastal", onset: "multi_day", drivers: ["wind", "water"], secondary: ["surge"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaCyclone.label, sourceUrl: SOURCES.noaaCyclone.url, coordinateNote: "Reference location in the Bay of Bengal region; not a track or wind field.", summary: "A documented cyclone used for metadata comparison only." },
  { id: "katrina-2005", name: "Hurricane Katrina", year: 2005, dateLabel: "2005", country: "United States", center: [-89.6, 29.5], hazard: "cyclone", setting: "coastal", onset: "multi_day", drivers: ["wind", "water"], secondary: ["surge"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaCyclone.label, sourceUrl: SOURCES.noaaCyclone.url, coordinateNote: "Reference Gulf Coast location; not a track or inundation footprint.", summary: "A documented tropical cyclone with wind and water driver traits." },
  { id: "haiyan-2013", name: "Typhoon Haiyan", year: 2013, dateLabel: "2013", country: "Philippines", center: [125, 11], hazard: "cyclone", setting: "island", onset: "multi_day", drivers: ["wind", "water"], secondary: ["surge"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaCyclone.label, sourceUrl: SOURCES.noaaCyclone.url, coordinateNote: "Reference Philippines location; not a forecast or observed wind field.", summary: "A documented tropical cyclone in the source-linked historical catalogue." },
  { id: "maria-2017", name: "Hurricane Maria", year: 2017, dateLabel: "2017", country: "Dominica", center: [-61.4, 15.3], hazard: "cyclone", setting: "island", onset: "multi_day", drivers: ["wind", "water"], secondary: ["surge", "landslide"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaCyclone.label, sourceUrl: SOURCES.noaaCyclone.url, coordinateNote: "Reference island location; not a track, wind field, or damage footprint.", summary: "A documented tropical cyclone with categorical secondary-hazard context." },
  { id: "idai-2019", name: "Cyclone Idai", year: 2019, dateLabel: "2019", country: "Mozambique", center: [34.9, -19.8], hazard: "cyclone", setting: "coastal", onset: "multi_day", drivers: ["wind", "water"], secondary: ["surge"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference Mozambique location; not a storm track or flood extent.", summary: "A documented cyclone represented by a reference coordinate for visual navigation." },
  { id: "mississippi-1993", name: "Great Flood of 1993", year: 1993, dateLabel: "1993", country: "United States", center: [-90.2, 38.9], hazard: "flood", setting: "inland", onset: "seasonal", drivers: ["water"], secondary: [], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference Mississippi River location; not an inundation footprint.", summary: "A documented flood represented by a river-basin reference point only." },
  { id: "pakistan-flood-2010", name: "Pakistan floods", year: 2010, dateLabel: "2010", country: "Pakistan", center: [71.2, 30.4], hazard: "flood", setting: "inland", onset: "seasonal", drivers: ["water"], secondary: ["landslide"], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference Pakistan location; not a flood-depth or inundation map.", summary: "A documented flood event used only for categorical metadata comparison." },
  { id: "thailand-flood-2011", name: "Thailand floods", year: 2011, dateLabel: "2011", country: "Thailand", center: [100.5, 14], hazard: "flood", setting: "inland", onset: "seasonal", drivers: ["water"], secondary: [], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference central Thailand location; not a flood extent.", summary: "A documented flood in the curated historical catalogue." },
  { id: "pakistan-flood-2022", name: "Pakistan floods", year: 2022, dateLabel: "2022", country: "Pakistan", center: [69.3, 30.4], hazard: "flood", setting: "inland", onset: "seasonal", drivers: ["water"], secondary: [], sourceFamily: "noaa", sourceLabel: SOURCES.noaaClimate.label, sourceUrl: SOURCES.noaaClimate.url, coordinateNote: "Reference Pakistan location; not an observed flood boundary.", summary: "A documented flood event represented for catalogue navigation, not flood modelling." },
  { id: "camp-fire-2018", name: "Camp Fire", year: 2018, dateLabel: "2018", country: "United States", center: [-121.44, 39.81], hazard: "wildfire", setting: "inland", onset: "rapid", drivers: ["thermal"], secondary: ["smoke"], sourceFamily: "official_other", sourceLabel: SOURCES.officialFire.label, sourceUrl: SOURCES.officialFire.url, coordinateNote: "Reference origin area; not a fire perimeter.", summary: "A documented wildfire encoded as categorical context, not fire behaviour or loss." },
  { id: "black-summer-2019", name: "Australian Black Summer bushfires", year: 2019, dateLabel: "2019–20", country: "Australia", center: [150, -35.5], hazard: "wildfire", setting: "coastal", onset: "seasonal", drivers: ["thermal"], secondary: ["smoke"], sourceFamily: "official_other", sourceLabel: SOURCES.officialFire.label, sourceUrl: SOURCES.officialFire.url, coordinateNote: "Reference southeast Australia location; not a perimeter or burn-severity layer.", summary: "A documented bushfire season represented by a regional reference location." },
  { id: "maui-2023", name: "Maui wildfires", year: 2023, dateLabel: "2023", country: "United States", center: [-156.68, 20.89], hazard: "wildfire", setting: "island", onset: "rapid", drivers: ["thermal", "wind"], secondary: ["smoke"], sourceFamily: "official_other", sourceLabel: SOURCES.officialFire.label, sourceUrl: SOURCES.officialFire.url, coordinateNote: "Reference Lahaina-area location; not a perimeter or damage footprint.", summary: "A documented wildfire represented as a source-linked reference location only." },
  { id: "pinatubo-1991", name: "Mount Pinatubo eruption", year: 1991, dateLabel: "1991", country: "Philippines", center: [120.35, 15.13], hazard: "volcano", setting: "mountain", onset: "multi_day", drivers: ["ash"], secondary: ["lahar"], sourceFamily: "official_other", sourceLabel: SOURCES.officialVolcano.label, sourceUrl: SOURCES.officialVolcano.url, coordinateNote: "Reference volcano location; not an ashfall, lahar, or exclusion zone.", summary: "A documented eruption with lahar context encoded only as a catalogue trait." },
  { id: "eyjafjallajokull-2010", name: "Eyjafjallajökull eruption", year: 2010, dateLabel: "2010", country: "Iceland", center: [-19.62, 63.63], hazard: "volcano", setting: "island", onset: "multi_day", drivers: ["ash"], secondary: [], sourceFamily: "official_other", sourceLabel: SOURCES.officialVolcano.label, sourceUrl: SOURCES.officialVolcano.url, coordinateNote: "Reference volcano location; not an ash cloud or airspace-impact footprint.", summary: "A documented eruption in the source-linked historical catalogue." },
];

export function eraFor(year: number): GenomeEra {
  if (year < 2000) return "pre_2000";
  if (year < 2010) return "2000s";
  if (year < 2020) return "2010s";
  return "2020s";
}

export function traitVector(event: HistoricalGenomeEvent): number[] {
  const era = eraFor(event.year);
  return GENOME_TRAITS.map((trait) => {
    if (trait.id === `hazard_${event.hazard}`) return 1;
    if (trait.id === `era_${era}`) return 1;
    if (trait.id === `setting_${event.setting}`) return 1;
    if (trait.id === `onset_${event.onset}`) return 1;
    if (trait.id.startsWith("driver_") && event.drivers.includes(trait.id.replace("driver_", "") as GenomeDriver)) return 1;
    if (trait.id === "secondary_compound") return event.secondary.length >= 2 ? 1 : 0;
    if (trait.id.startsWith("secondary_") && event.secondary.includes(trait.id.replace("secondary_", "") as GenomeSecondary)) return 1;
    if (trait.id === `archive_${event.sourceFamily}`) return 1;
    return 0;
  });
}

export function euclideanDistance(first: HistoricalGenomeEvent, second: HistoricalGenomeEvent): number {
  const a = traitVector(first);
  const b = traitVector(second);
  return Math.sqrt(a.reduce((sum, value, index) => sum + (value - b[index]) ** 2, 0));
}

export function similarityPercent(first: HistoricalGenomeEvent, second: HistoricalGenomeEvent): number {
  const maxDistance = Math.sqrt(GENOME_TRAITS.length);
  return Math.round(Math.max(0, (1 - euclideanDistance(first, second) / maxDistance) * 100));
}

export function nearestNeighbors(event: HistoricalGenomeEvent, take = 3) {
  return HISTORICAL_GENOME_EVENTS
    .filter((candidate) => candidate.id !== event.id)
    .map((candidate) => ({ event: candidate, distance: euclideanDistance(event, candidate), similarity: similarityPercent(event, candidate) }))
    .sort((a, b) => a.distance - b.distance || b.event.year - a.event.year)
    .slice(0, take);
}

export function outlierDistance(event: HistoricalGenomeEvent, neighbors = 3): number {
  const matches = nearestNeighbors(event, neighbors);
  return matches.reduce((sum, match) => sum + match.distance, 0) / Math.max(matches.length, 1);
}

export function hazardColor(hazard: GenomeHazard) {
  if (hazard === "earthquake") return "#9C7BFF";
  if (hazard === "cyclone") return "#FF8A3D";
  if (hazard === "flood") return "#4FA8FF";
  if (hazard === "wildfire") return "#F2533D";
  return "#E0B64A";
}
