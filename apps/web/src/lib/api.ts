import type {
  AssistantAnswer,
  CascadeResult,
  EvidenceTrail,
  HiddenRisk,
  HistoricalAnalog,
  ImpactSequence,
  IncidentDetail,
  IncidentSummary,
  LiveEventsResponse,
  GlobalEventsResponse,
  GlobalOutlookResponse,
  LocationCapsule,
  ModelCard,
  MultiHazardOverview,
  PlaceSearchResult,
  PortfolioExposure,
  RegionSummary,
  RouteAnalyzeResponse,
  Scenario,
  ScenarioResult,
  SourceStatus,
  WhatChanged,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  liveSummary: () => request<RegionSummary>("/live/summary"),
  liveEvents: () => request<LiveEventsResponse>("/live/events"),
  globalEvents: () => request<GlobalEventsResponse>("/live/global-events"),
  globalOutlook: (horizonMinutes: number) => request<GlobalOutlookResponse>(`/live/global-outlook?horizon_minutes=${Math.max(0, Math.min(1440, Math.round(horizonMinutes)))}`),
  multiHazardOverview: () => request<MultiHazardOverview>("/live/multi-hazard"),

  searchPlaces: (q: string) =>
    request<{ query: string; results: PlaceSearchResult[] }>(`/places/search?q=${encodeURIComponent(q)}`),
  getPlaceCapsule: (placeId: string) => request<LocationCapsule>(`/places/${placeId}/capsule`),

  listIncidents: (mode: "live" | "replay" = "live") =>
    request<IncidentSummary[]>(`/incidents?mode=${mode}`),
  getIncident: (incidentId: string, mode: "live" | "replay" = "live") =>
    request<IncidentDetail>(`/incidents/${incidentId}?mode=${mode}`),
  getIncidentForecast: (incidentId: string, mode: "live" | "replay" = "live") =>
    request<ImpactSequence>(`/incidents/${incidentId}/forecast?mode=${mode}`),
  getIncidentImpacts: (incidentId: string, mode: "live" | "replay" = "live") =>
    request<CascadeResult>(`/incidents/${incidentId}/impacts?mode=${mode}`),
  getIncidentEvidence: (incidentId: string, mode: "live" | "replay" = "live") =>
    request<EvidenceTrail[]>(`/incidents/${incidentId}/evidence?mode=${mode}`),
  getWhatChanged: (
    incidentId: string,
    comparedTo: "30_minutes" | "1_hour" | "6_hours" | "yesterday",
    mode: "live" | "replay" = "live",
  ) => request<WhatChanged>(`/incidents/${incidentId}/what-changed?mode=${mode}&compared_to=${comparedTo}`),
  getAnalogs: (incidentId: string) => request<HistoricalAnalog[]>(`/incidents/${incidentId}/analogs`),

  analyzeRoute: (originPlaceId: string, destinationPlaceId: string) =>
    request<RouteAnalyzeResponse>("/routes/analyze", {
      method: "POST",
      body: JSON.stringify({ origin_place_id: originPlaceId, destination_place_id: destinationPlaceId }),
    }),

  createScenario: (body: Partial<Scenario> & { actions?: string[] }) =>
    request<Scenario>("/scenarios", { method: "POST", body: JSON.stringify(body) }),
  runScenario: (scenarioId: string) =>
    request<ScenarioResult>(`/scenarios/${scenarioId}/run`, { method: "POST" }),
  getScenarioResults: (scenarioId: string) =>
    request<ScenarioResult>(`/scenarios/${scenarioId}/results`),

  queryAssistant: (question: string) =>
    request<AssistantAnswer>("/assistant/query", { method: "POST", body: JSON.stringify({ question }) }),

  sourceStatus: () => request<SourceStatus[]>("/sources/status"),
  listModels: () => request<ModelCard[]>("/models"),
  hiddenRisks: () => request<HiddenRisk[]>("/risks/hidden"),

  uploadPortfolio: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE_URL}/portfolio/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, body || res.statusText);
    }
    return res.json() as Promise<PortfolioExposure>;
  },
};
