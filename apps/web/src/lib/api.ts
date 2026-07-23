import type {
  AssistantAnswer,
  CommunitySignalsResponse,
  AssistantContext,
  CascadeResult,
  CommunityPulseResponse,
  EvidenceTrail,
  HiddenRisk,
  HistoricalAnalog,
  ImpactSequence,
  IncidentDetail,
  IncidentSummary,
  LiveEventsResponse,
  NewsArticlesResponse,
  GlobalEventsResponse,
  FutureOutlookResponse,
  ModelWeatherOutlookResponse,
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
  CatModelRunResult,
  AnalysisHazard, AnalysisMode, AnalysisLocation, AnalysisRunResult, HazardEventSearchResponse,
  DataCoverageItem,
  ProbabilisticResult,
  VulnerabilityFunction,
  ModelResultLayer,
  LearnLessonSummary,
  LearnLesson,
  ResearchSearchResponse,
  RoadmapResponse,
  CopilotAnswer,
  WhatChanged,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(body: string, fallback: string) {
  if (!body) return fallback;
  try {
    const parsed = JSON.parse(body) as { detail?: string | Array<{ msg?: string }> };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) return parsed.detail.map((item) => item.msg).filter(Boolean).join("; ") || fallback;
  } catch {
    // Plain-text upstream errors are still useful, but never render an HTML error page.
  }
  return body.includes("<html") ? fallback : body.slice(0, 280);
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const abortFromCaller = () => controller.abort();
  init?.signal?.addEventListener("abort", abortFromCaller, { once: true });
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      // Do not attach Content-Type to GET requests. Besides being inaccurate,
      // it turns otherwise simple cross-origin geocoder reads into a CORS
      // preflight, which makes type-ahead look stalled on a cold connection.
      headers: { ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, errorMessage(body, res.statusText || "Request failed"));
    }
    return await res.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) throw new ApiError(408, "The service took too long to respond. Please retry; the control has been re-enabled.");
    throw error;
  } finally {
    window.clearTimeout(timeout);
    init?.signal?.removeEventListener("abort", abortFromCaller);
  }
}

export const api = {
  liveSummary: () => request<RegionSummary>("/live/summary"),
  liveEvents: () => request<LiveEventsResponse>("/live/events"),
  globalEvents: () => request<GlobalEventsResponse>("/live/global-events"),
  refreshGlobalEvents: () => request<GlobalEventsResponse>("/live/global-events?force=true"),
  newsArticles: (
    hazard: "all" | "flood" | "wildfire" | "earthquake" | "storm" | "drought" = "all",
    hours = 24,
    force = false,
  ) => request<NewsArticlesResponse>(`/news/articles?hazard=${encodeURIComponent(hazard)}&hours=${Math.max(1, Math.min(168, Math.round(hours)))}${force ? "&force=true" : ""}`),
  globalOutlook: (horizonMinutes: number) => request<GlobalOutlookResponse>(`/live/global-outlook?horizon_minutes=${Math.max(0, Math.min(1440, Math.round(horizonMinutes)))}`),
  futureOutlook: (targetAt: string) => request<FutureOutlookResponse>(`/live/future-outlook?target_at=${encodeURIComponent(targetAt)}`),
  modelWeatherOutlook: (targetAt: string, center: [number, number], locationName: string) => request<ModelWeatherOutlookResponse>(
    `/live/model-weather-outlook?target_at=${encodeURIComponent(targetAt)}&latitude=${encodeURIComponent(center[1])}&longitude=${encodeURIComponent(center[0])}&location_name=${encodeURIComponent(locationName)}`,
  ),
  communitySignals: (eventId: string) => request<CommunitySignalsResponse>(`/live/community-signals/${encodeURIComponent(eventId)}`),
  multiHazardOverview: () => request<MultiHazardOverview>("/live/multi-hazard"),
  communityPulse: (incidentId = "developing-flood-bethlehem") =>
    request<CommunityPulseResponse>(`/community/pulse?incident_id=${encodeURIComponent(incidentId)}`),

  searchPlaces: (q: string, signal?: AbortSignal) =>
    request<{ query: string; results: PlaceSearchResult[] }>(`/places/search?q=${encodeURIComponent(q)}`, { signal }),
  suggestPlaces: (q: string, signal?: AbortSignal) =>
    request<{ query: string; results: PlaceSearchResult[] }>(`/places/suggest?q=${encodeURIComponent(q)}`, { signal }),
  resolvePlace: (place: PlaceSearchResult) => request<PlaceSearchResult>(`/places/resolve?lon=${encodeURIComponent(place.center[0])}&lat=${encodeURIComponent(place.center[1])}&name=${encodeURIComponent(place.name)}&place_id=${encodeURIComponent(place.place_id)}`),
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

  queryAssistant: (question: string, context?: AssistantContext) =>
    request<AssistantAnswer>("/assistant/query", { method: "POST", body: JSON.stringify({ question, context }) }),

  sourceStatus: () => request<SourceStatus[]>("/sources/status"),
  listModels: () => request<ModelCard[]>("/models"),
  hiddenRisks: () => request<HiddenRisk[]>("/risks/hidden"),

  runCatFloodModel: (body: {
    scenario_label: string;
    deductible_usd: number;
    limit_usd: number | null;
    coinsurance: number;
    seed: number;
    iterations: number;
  }) => request<CatModelRunResult>("/cat/model-runs", {
    method: "POST",
    body: JSON.stringify(body),
  }),
  hazardEvents: (mode: Exclude<AnalysisMode,"demo">, hazard: AnalysisHazard, startDate?:string,endDate?:string) => { const params=new URLSearchParams({mode,hazard_type:hazard}); if(startDate)params.set("start_date",startDate); if(endDate)params.set("end_date",endDate); return request<HazardEventSearchResponse>(`/cat/hazard-events?${params.toString()}`); },
  runAnalysis: (body:{mode:Exclude<AnalysisMode,"demo">;hazard_type:AnalysisHazard;location?:AnalysisLocation|null;provider?:string|null;event_id?:string|null;advisory_id?:string|null;threshold?:string|null;return_period_years?:number|null;start_date?:string|null;end_date?:string|null;exposure_dataset?:string;vulnerability_model?:string|null;simulation_count?:number;seed?:number}) => request<AnalysisRunResult>("/cat/analyses",{method:"POST",body:JSON.stringify(body)},45_000),
  catDataCoverage: () => request<DataCoverageItem[]>("/cat/data-coverage"),
  catVulnerabilityFunctions: () => request<VulnerabilityFunction[]>("/cat/vulnerability-functions"),
  catProbabilisticResults: (runId: string, years = 5000) =>
    request<ProbabilisticResult>(`/cat/model-runs/${encodeURIComponent(runId)}/probabilistic?years=${years}`),
  catProbabilisticPreview: (medianEventLossUsd: number, years = 5000) =>
    request<ProbabilisticResult>("/cat/probabilistic-preview", {
      method: "POST",
      body: JSON.stringify({ median_event_loss_usd: medianEventLossUsd, years }),
    }),
  catRunLayer: (runId: string, layerId: "damage-ratio" | "flood-depth" | "ground-up-loss" | "insured-loss") =>
    request<ModelResultLayer>(`/cat/model-runs/${encodeURIComponent(runId)}/layers/${layerId}`),
  learnLessons: () => request<LearnLessonSummary[]>("/learn/lessons"),
  learnLesson: (lessonId: string) => request<LearnLesson>(`/learn/lessons/${encodeURIComponent(lessonId)}`),
  researchSearch: (query: string, hazard?: string, assetType?: string) =>
    request<ResearchSearchResponse>("/research/search", {
      method: "POST",
      body: JSON.stringify({ query, hazard: hazard || null, asset_type: assetType || null }),
    }),
  roadmap: () => request<RoadmapResponse>("/roadmap"),
  queryCopilot: (message: string, context?: { hazard?: string; location_label?: string; run_id?: string; interface_mode?: string }) =>
    request<CopilotAnswer>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify({ message, context: { user_role: "learner", interface_mode: "guided", permissions: [], ...context } }),
    }),
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
