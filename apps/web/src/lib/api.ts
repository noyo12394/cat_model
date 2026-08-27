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
type NewsTopic = "all" | "flood" | "wildfire" | "earthquake" | "storm" | "drought" | "cat_model" | "resilience";
export type LiveWindow = "24h" | "7d" | "30d" | "90d" | "ytd";
export type GlobalEventQuery = {
  window?: LiveWindow;
  alert?: string;
  hazard?: string;
  region?: string;
  q?: string;
  from?: string;
  to?: string;
  min_impact?: number;
  start_date?: string;
  end_date?: string;
  force?: boolean;
};

function globalEventPath(query: GlobalEventQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== "all" && value !== false) params.set(key, String(value));
  });
  const suffix = params.toString();
  return `/live/global-events${suffix ? `?${suffix}` : ""}`;
}

const GDELT_NEWS_QUERIES: Record<NewsTopic, { query: string; label: string }> = {
  all: {
    query: '(imagetag:"flood" OR imagetag:"earthquake" OR imagetag:"fire" OR imagetag:"hurricane" OR cyclone OR "tropical storm" OR landslide OR tsunami OR drought OR "catastrophe model" OR "catastrophe modelling" OR "disaster resilience" OR "climate resilience")',
    label: "Global hazards, catastrophe modelling and resilience",
  },
  flood: { query: '(imagetag:"flood" OR "flash flood" OR inundation)', label: "Flooding" },
  wildfire: { query: '(imagetag:"fire" OR wildfire OR "forest fire" OR bushfire)', label: "Wildfire" },
  earthquake: { query: '(imagetag:"earthquake" OR earthquake OR aftershock OR tsunami)', label: "Earthquake and tsunami" },
  storm: { query: '(imagetag:"hurricane" OR hurricane OR cyclone OR typhoon OR "tropical storm" OR tornado OR "severe weather")', label: "Storm and wind" },
  drought: { query: '(drought OR "extreme heat" OR heatwave)', label: "Drought and heat" },
  cat_model: { query: '("catastrophe model" OR "catastrophe modelling" OR "catastrophe modeling" OR "disaster risk model" OR "flood damage modelling" OR "fragility curve")', label: "Catastrophe modelling" },
  resilience: { query: '("disaster resilience" OR "climate resilience" OR "resilient infrastructure" OR "climate adaptation" OR "disaster risk reduction")', label: "Disaster resilience and adaptation" },
};

function gdeltDate(value: unknown) {
  if (typeof value !== "string" || !/^\d{8}T\d{6}Z$/.test(value)) return null;
  const iso = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}T${value.slice(9, 11)}:${value.slice(11, 13)}:${value.slice(13, 15)}Z`;
  return Number.isNaN(Date.parse(iso)) ? null : iso;
}

async function browserGdeltNews(hazard: NewsTopic, hours: number): Promise<NewsArticlesResponse> {
  const safeHours = Math.max(1, Math.min(168, Math.round(hours)));
  const topic = GDELT_NEWS_QUERIES[hazard];
  const url = new URL("https://api.gdeltproject.org/api/v2/doc/doc");
  url.search = new URLSearchParams({ query: topic.query, mode: "artlist", format: "json", sort: "datedesc", timespan: `${safeHours}h`, maxrecords: "50" }).toString();
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new ApiError(response.status, "The public GDELT article index did not return a readable result.");
  const payload = await response.json() as { articles?: unknown[] };
  if (!Array.isArray(payload.articles)) throw new ApiError(502, "The public GDELT article index returned an unexpected response.");
  const seen = new Set<string>();
  const articles = payload.articles.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const articleUrl = typeof record.url === "string" ? record.url : null;
    const title = typeof record.title === "string" ? record.title.trim().replace(/\s+/g, " ") : null;
    const publishedAt = gdeltDate(record.seendate);
    if (!articleUrl || !/^https?:\/\//.test(articleUrl) || !title || !publishedAt || seen.has(articleUrl)) return [];
    seen.add(articleUrl);
    return [{
      article_id: `gdelt-browser-${articleUrl}`,
      title,
      url: articleUrl,
      publisher_domain: typeof record.domain === "string" && record.domain ? record.domain : "Publisher not reported",
      source_country: typeof record.sourcecountry === "string" ? record.sourcecountry : null,
      language: typeof record.language === "string" ? record.language : null,
      published_at: publishedAt,
    }];
  });
  return {
    articles,
    data_status: "live",
    retrieved_at: new Date().toISOString(),
    query_label: topic.label,
    hazard_filter: hazard,
    hours: safeHours,
    source_name: "GDELT DOC 2.0 Article List",
    source_url: "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
    notice: "Publisher headlines are a live discovery index, not verified observations, official alerts, model inputs, or loss estimates. Open the original source and corroborate before acting.",
  };
}

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

async function request<T>(path: string, init?: RequestInit, timeoutMs = 30_000, baseUrl = BASE_URL): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const abortFromCaller = () => controller.abort();
  init?.signal?.addEventListener("abort", abortFromCaller, { once: true });
  try {
    const res = await fetch(`${baseUrl}${path}`, {
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
  globalEvents: (query: GlobalEventQuery = {}) => request<GlobalEventsResponse>(globalEventPath(query), undefined, 45_000),
  refreshGlobalEvents: (query: GlobalEventQuery = {}) => request<GlobalEventsResponse>(globalEventPath({ ...query, force: true }), undefined, 45_000),
  newsArticles: (
    hazard: NewsTopic = "all",
    hours = 24,
    force = false,
  ) => request<NewsArticlesResponse>(`/news/articles?hazard=${encodeURIComponent(hazard)}&hours=${Math.max(1, Math.min(168, Math.round(hours)))}${force ? "&force=true" : ""}`)
    .then((response) => response.data_status === "unavailable" ? browserGdeltNews(hazard, hours) : response)
    .catch(() => browserGdeltNews(hazard, hours)),
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
  runAnalysis: (body:{mode:Exclude<AnalysisMode,"demo">;hazard_type:AnalysisHazard;location?:AnalysisLocation|null;provider?:string|null;event_id?:string|null;advisory_id?:string|null;threshold?:string|null;return_period_years?:number|null;start_date?:string|null;end_date?:string|null;exposure_dataset?:string;vulnerability_model?:string|null;simulation_count?:number;seed?:number}) => request<AnalysisRunResult>("/cat/analyses",{method:"POST",credentials:"omit",body:JSON.stringify(body)},90_000,"/api-proxy"),
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
