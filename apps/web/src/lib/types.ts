// Mirrors apps/api/app/schemas/*.py. Kept as hand-written interfaces (rather
// than generated) so the shapes are easy to read alongside the Python
// source; see docs/API_SPEC.md for the authoritative endpoint list.

export type CertaintyClass =
  | "observed"
  | "official_alert"
  | "forecast"
  | "ai_inferred"
  | "user_reported"
  | "unverified"
  | "historical"
  | "simulated";

export type Confidence = "low" | "moderate" | "high";
export type Severity = "unknown" | "normal" | "watch" | "elevated" | "severe" | "extreme";
export type DataStatus = "live" | "stale" | "unavailable" | "demo";
export type AnalysisMode = "live" | "historical" | "hypothetical" | "demo";
export type AnalysisHazard = "hurricane" | "earthquake" | "flood" | "wildfire";
export interface AnalysisLocation { place_id:string; name:string; center:[number,number]; bbox?:[number,number,number,number]|null; state?:string|null; state_fips?:string|null; county?:string|null; county_fips?:string|null; tract?:string|null; tract_geoid?:string|null; geography_vintage?:string|null; }
export interface HazardEventSummary { provider:string; provider_event_id:string; hazard_type:AnalysisHazard; name:string; status:string; start_time?:string|null; update_time?:string|null; center?:[number,number]|null; source_url:string; source_version:string; classification:"observed"|"forecast"|"scenario"; advisory_id?:string|null; footprint_available:boolean; limitations:string[]; }
export interface HazardEventSearchResponse { events:HazardEventSummary[]; provider:string; retrieved_at:string; data_status:"live"|"unavailable"; message?:string|null; }
export interface AnalysisRunResult { run_id:string; result_type:"exposure_screening"|"loss_estimate"; mode:AnalysisMode; hazard_type:AnalysisHazard; title:string; provider_event_id?:string|null; event_time?:string|null; analysis_time:string; geography?:AnalysisLocation|null; hazard_threshold?:string|null; hazard_layers:Array<{id:string;name:string;geojson:{type:"FeatureCollection";features:unknown[]};classification:string;observed_forecast_modelled:string}>; totals:{structures?:number|null;population?:number|null;structure_value_usd?:number|null;contents_value_usd?:number|null;valid_assets:number;excluded_assets:number}; confidence:{overall:string;components:Record<string,string>;explanation:string;ways_to_improve:string[]}; component_status:Record<string,string>; limitations:string[]; loss?:Record<string,unknown>|null; manifest:Record<string,unknown>&{run_id:string;created_at:string}; }

export interface LossDistribution {
  mean_usd: number;
  p10_usd: number;
  p50_usd: number;
  p90_usd: number;
  range_low_usd: number;
  range_high_usd: number;
  std_usd: number;
  samples: number;
  method: string;
}

export interface CatAuditFinding {
  code: string;
  severity: "info" | "warning" | "high" | string;
  title: string;
  detail: string;
  recommendation: string;
}

export interface CatModelRunResult {
  run_id: string;
  scenario_label: string;
  hazard_type: string;
  region_label: string;
  is_demo: boolean;
  data_status: DataStatus;
  resolution: {
    analysis_resolution: string;
    hazard_resolution: string;
    population_resolution: string;
    building_use_origin: string;
  };
  asset_count: number;
  financial_terms: {
    deductible_usd: number;
    limit_usd?: number | null;
    coinsurance: number;
    currency: string;
  };
  asset_damage: AssetDamageResult[];
  asset_financial: AssetFinancialResult[];
  ground_up_distribution: LossDistribution;
  gross_distribution: LossDistribution;
  net_insured_distribution: LossDistribution;
  confidence: { band: Confidence; drivers: string[]; largest_uncertainty: string };
  audit_findings: CatAuditFinding[];
  assumptions: { label: string; value: string; origin: string }[];
  sources: Provenance[];
  limitations: string[];
  manifest: {
    run_id: string;
    created_at: string;
    code_version: string;
    model_ids: Record<string, string>;
    random_seed: number;
    parameters: Record<string, string | number>;
    input_summary: Record<string, string | number>;
    parent_run_id?: string | null;
  };
}

export interface AssetDamageResult {
  asset_id: string;
  intensity: number;
  mean_damage_ratio: number;
  damage_state_probabilities: Record<string, number>;
  building_loss_usd: number;
  contents_loss_usd: number;
  business_interruption_loss_usd: number;
  ground_up_loss_usd: number;
  extrapolated: boolean;
  vulnerability_function_id: string;
}

export interface AssetFinancialResult {
  asset_id: string;
  ground_up_loss_usd: number;
  deductible_applied_usd: number;
  gross_loss_usd: number;
  net_insured_loss_usd: number;
  currency: string;
}

export interface VulnerabilityFunction {
  function_id: string;
  name: string;
  hazard: string;
  asset_class: string;
  intensity_measure: { name: string; label: string; unit: string };
  curve: { intensity: number; mean_damage_ratio: number }[];
  calibration_min: number;
  calibration_max: number;
  damage_ratio_cov: number;
  source: Provenance;
  applicability_notes: string;
  prohibited_extrapolations: string;
  version: string;
  approval_status: string;
}

export interface EPCurvePoint {
  return_period_years: number;
  exceedance_probability: number;
  loss_usd: number;
}

export interface ProbabilisticResult {
  basis: string;
  aal_usd: number;
  event_count: number;
  simulation_years: number;
  oep_curve: EPCurvePoint[];
  aep_curve: EPCurvePoint[];
  var: { quantile: number; loss_usd: number }[];
  tvar: { quantile: number; loss_usd: number }[];
  method: string;
  assumptions: string[];
  limitations: string[];
}

export interface ModelResultLayer {
  run_id: string;
  layer_id: string;
  title: string;
  geometry_type: string;
  data_status: DataStatus;
  geojson: {
    type: "FeatureCollection";
    features: Array<{
      id?: string;
      geometry: { type: "Point"; coordinates: [number, number] };
      properties: { asset_id: string; name: string; occupancy: string; value: number; unit: string; extrapolated?: boolean };
    }>;
  };
  value_field: string;
  value_unit: string;
  provenance_note: string;
  limitations: string[];
}

export interface DataCoverageItem {
  layer_id: string;
  label: string;
  availability: "available_demo" | "available_live" | "unavailable";
  use_in_run: string;
  source: string;
  geographic_resolution: string;
  temporal_resolution: string;
  attribute_origin: string;
  limitations: string[];
}

export interface LearnLessonSummary {
  lesson_id: string;
  order: number;
  title: string;
  one_sentence: string;
}

export interface LearnLesson extends LearnLessonSummary {
  plain_language: string;
  technical_definition: string;
  formula?: string | null;
  interactive_example: string;
  common_mistake: string;
  real_world_use: string;
  platform_link: string;
  knowledge_check: {
    question: string;
    options: string[];
    answer_index: number;
    explanation: string;
  };
}

export interface ResearchPaperSummary {
  paper_id: string;
  title: string;
  publisher: string;
  year?: number | null;
  hazard: string;
  asset_type: string;
  relevance: number;
  peer_review_status: string;
  human_review_status: string;
}

export interface ResearchSearchResponse {
  query: string;
  reformulated_terms: string[];
  results: ResearchPaperSummary[];
  source_status: { source: string; status: string; note: string }[];
  notice: string;
}

export interface RoadmapMilestone {
  stage: string;
  name: string;
  owner_role: string;
  budget_band: string;
  timeline: string;
  acceptance_gate: string;
  exit_criteria: string[];
  status: string;
}

export interface RoadmapResponse {
  stages: string[];
  milestones: RoadmapMilestone[];
  notice: string;
}

export interface CopilotAnswer {
  response_type: string;
  mode: string;
  message: string;
  tool_trace: { id: string; tool: string; status: string; summary: string }[];
  citations: { source_id: string; label?: string | null; url?: string | null }[];
  disclaimers: string[];
  numbers_source: "approved_tools" | "none";
  prose_source: string;
  generated_at: string;
}

export interface TimeRange {
  start: string;
  end?: string | null;
  label?: string | null;
}

export interface Provenance {
  source: string;
  source_organization: string;
  source_url?: string | null;
  license?: string | null;
  observed_at?: string | null;
  updated_at?: string | null;
  retrieved_at: string;
  data_status: DataStatus;
  staleness_minutes?: number | null;
}

export interface ModelBasis {
  model_id: string;
  model_version: string;
  run_at: string;
  inputs_used: string[];
  confidence_method: string;
}

export interface EvidenceItem {
  label: string;
  detail?: string | null;
  provenance?: Provenance | null;
}

export interface EvidenceTrail {
  claim: string;
  certainty_class: CertaintyClass;
  confidence: Confidence;
  supporting_evidence: EvidenceItem[];
  weaknesses: string[];
  model_basis?: ModelBasis | null;
  plain_language_summary: string;
}

export type Geometry =
  | { type: "Point"; coordinates: [number, number] }
  | { type: "Polygon"; coordinates: [number, number][][] }
  | { type: "LineString"; coordinates: [number, number][] };

export interface RegionSummary {
  region_label: string;
  active_incident_count: number;
  active_alert_count: number;
  rising_gauge_count: number;
  headline: string;
  generated_at: string;
  is_demo: boolean;
}

export interface GlobalEvent {
  event_id: string;
  event_type: string;
  name: string;
  country: string;
  alert_level: "green" | "orange" | "red" | string;
  alert_score?: number | null;
  severity_text: string;
  from_date: string;
  to_date: string;
  modified_at: string;
  center: [number, number];
  source: string;
  report_url: string;
  geometry_url?: string | null;
  is_current: boolean;
  data_status: DataStatus;
}

export interface GlobalEventsResponse {
  events: GlobalEvent[];
  counts: { total: number; red: number; orange: number; green: number };
  fetched_at: string;
  source_updated_at?: string | null;
  source_name: string;
  source_url: string;
  attribution: string;
  standards: string[];
  data_status: DataStatus;
  stale: boolean;
  result_cap: number;
  possibly_truncated: boolean;
  notice: string;
  error?: string | null;
  feed_state: "feed_ok" | "feed_ok_no_events" | "feed_degraded" | "feed_error";
  requested_window: string;
  effective_window: string;
  window_start?: string | null;
  window_end?: string | null;
  auto_widened: boolean;
  last_successful_poll_at?: string | null;
  query_endpoint?: string | null;
  query_parameters: Record<string, string | number>;
  local_filters?: Record<string, string | number>;
  feed_message?: string | null;
  response_mode?: "upstream" | "memory_cache" | "partial_upstream" | "checked_in_snapshot" | "none";
  snapshot_retrieved_at?: string | null;
}

export interface GlobalWatchItem {
  event_id: string;
  name: string;
  event_type: string;
  country: string;
  center: [number, number];
  alert_level: "green" | "orange" | "red" | string;
  alert_score?: number | null;
  modified_at: string;
  priority_score: number;
  priority_label: string;
  drivers: string[];
  next_action: string;
  report_url: string;
}

export interface GlobalOutlookResponse {
  horizon_minutes: number;
  horizon_label: string;
  generated_at: string;
  data_status: DataStatus;
  source_updated_at?: string | null;
  method: string;
  method_detail: string;
  items: GlobalWatchItem[];
  source_name: string;
  source_url: string;
  attribution: string;
  limitations: string[];
  error?: string | null;
}

export interface FutureForecastEvent {
  event_id: string;
  name: string;
  event_type: "TC";
  storm_type: string;
  basin: string;
  headline?: string | null;
  observed_at?: string | null;
  coverage_status: "dated_track_point" | "official_advisory";
  forecast_valid_from?: string | null;
  forecast_valid_to?: string | null;
  selected_point_at?: string | null;
  selected_point_center?: [number, number] | null;
  advisory_url: string;
  track_url: string;
  certainty_class: "official_forecast";
}

export interface FutureOutlookResponse {
  target_at: string;
  horizon_hours: number;
  availability: "available" | "unavailable";
  availability_label: string;
  availability_detail: string;
  generated_at: string;
  data_status: DataStatus;
  items: FutureForecastEvent[];
  source_name: string;
  source_url: string;
  attribution: string;
  coverage: string;
  limitations: string[];
  error?: string | null;
}

export interface ModelWeatherMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  range_low?: number | null;
  range_high?: number | null;
  detail?: string | null;
}

export interface ModelWeatherOutlookResponse {
  target_at: string;
  horizon_hours: number;
  availability: "available" | "unavailable";
  availability_label: string;
  availability_detail: string;
  coverage_type: "short_range_ml" | "short_range_numerical" | "seasonal_ensemble" | "unavailable";
  location_name: string;
  center: [number, number];
  provider: string;
  model_name?: string | null;
  source_url: string;
  generated_at: string;
  data_status: DataStatus;
  metrics: ModelWeatherMetric[];
  reliability_note: string;
  limitations: string[];
  error?: string | null;
}

export interface CommunitySignal {
  post_id: string;
  text: string;
  observed_at: string;
  language?: string | null;
  tone: "urgent_language" | "concern_language" | "neutral_language";
  report_type: "possible_impact_report" | "possible_condition_report" | "event_mention";
  tags: string[];
  source_url: string;
  certainty_class: "user_reported";
  verification_status: "unverified";
}

export interface CommunitySignalsResponse {
  event_id: string;
  event_name: string;
  event_center: [number, number];
  availability: "available" | "unavailable";
  availability_label: string;
  availability_detail: string;
  generated_at: string;
  data_status: DataStatus;
  items: CommunitySignal[];
  source_name: string;
  source_url: string;
  method: string;
  limitations: string[];
  error?: string | null;
}

export interface PlaceSearchResult {
  place_id: string;
  name: string;
  center: [number, number];
  provider?: string;
  data_status?: DataStatus;
  zoom?: number;
  bbox?: [number, number, number, number] | null;
  state?: string | null;
  state_fips?: string | null;
  county?: string | null;
  county_fips?: string | null;
  tract?: string | null;
  tract_geoid?: string | null;
  geography_vintage?: string | null;
}

export interface NearbyCondition {
  label: string;
  certainty_class: string;
  detail?: string | null;
}

export interface CriticalConnection {
  facility_id: string;
  facility_type: string;
  name: string;
  distance_km: number;
  travel_time_minutes?: number | null;
}

export interface LocationCapsule {
  place_id: string;
  name: string;
  center: [number, number];
  current_status_headline: string;
  nearby_conditions: NearbyCondition[];
  next_24h_notes: string[];
  forecast_confidence: Confidence;
  critical_connections: CriticalConnection[];
  data_confidence: Confidence;
  last_updated: string;
  active_incident_ids: string[];
  is_demo: boolean;
}

export interface TimelineEntry {
  entry_id: string;
  at: string;
  label: string;
  detail: string;
  certainty_class: string;
  source: string;
  is_first_detection: boolean;
  is_peak: boolean;
  is_recovery: boolean;
}

export interface FusionReason {
  incident_id: string;
  matched_on: string[];
  match_confidence: Confidence;
  related_signal_ids: string[];
  explanation: string;
}

export interface IncidentSummary {
  incident_id: string;
  slug: string;
  title: string;
  hazard_type: string;
  severity: Severity;
  status: string;
  region_label: string;
  center: [number, number];
  geometry?: Geometry | null;
  created_at: string;
  updated_at: string;
  overall_confidence: Confidence;
  one_line_summary: string;
  related_signal_count: number;
  is_demo: boolean;
}

export interface IncidentDetail extends IncidentSummary {
  description: string;
  timeline: TimelineEntry[];
  fusion_reason?: FusionReason | null;
  affected_facility_ids: string[];
  affected_population_estimate?: number | null;
  affected_population_note: string;
  sources: string[];
}

export interface WhatChangedItem {
  label: string;
  detail: string;
  certainty_class: string;
  magnitude?: number | null;
  unit?: string | null;
}

export interface WhatChanged {
  incident_id: string;
  compared_to_label: string;
  compared_to_at: string;
  now_at: string;
  changes: WhatChangedItem[];
}

export interface ImpactStep {
  step_id: string;
  order: number;
  statement: string;
  time_window: TimeRange;
  confidence: Confidence;
  evidence_trail: EvidenceTrail;
}

export interface ImpactSequence {
  incident_id: string;
  title: string;
  observed_signals: string[];
  steps: ImpactStep[];
  overall_confidence: Confidence;
  model_basis: ModelBasis;
  disclaimer: string;
}

export interface HistoricalAnalog {
  analog_id: string;
  event_name: string;
  year: number;
  similarity_score: number;
  similarity_features: string[];
  what_happened_next: string;
  key_differences: string[];
  why_it_may_not_repeat: string[];
  data_quality: Confidence;
  source_url?: string | null;
}

export interface CascadeNode {
  facility_id: string;
  name: string;
  facility_type: string;
  operational_state: string;
  served_population: number;
  directly_exposed: boolean;
  hops_from_hazard?: number | null;
  estimated_minutes_to_consequence?: number | null;
  is_removed: boolean;
}

export interface CascadeEdge {
  from_facility_id: string;
  to_facility_id: string;
  relationship: string;
  strength: number;
  is_uncertain: boolean;
}

export interface CascadeResult {
  nodes: CascadeNode[];
  edges: CascadeEdge[];
  narrative: string[];
  assumptions: string[];
}

export interface RouteSegmentExposure {
  segment_id: string;
  description: string;
  hazard_overlap: boolean;
  hazard_labels: string[];
  river_crossing: boolean;
  reported_closure: boolean;
}

export interface RouteOption {
  route_id: string;
  label: string;
  duration_minutes?: number | null;
  distance_km?: number | null;
  geometry: Geometry;
  exposure_note: string;
  exposure_level: "lower" | "elevated" | "unavailable";
  segments: RouteSegmentExposure[];
  data_freshness_minutes?: number | null;
  confidence: string;
}

export interface RouteAnalyzeResponse {
  origin_place_id: string;
  destination_place_id: string;
  options: RouteOption[];
  disclaimer: string;
}

export interface Scenario {
  scenario_id: string;
  name: string;
  created_at: string;
  mode: string;
  location_label: string;
  center: [number, number];
  hazard_type: string;
  severity: string;
  duration_hours: number;
  time_of_day: string;
  river_condition?: string | null;
  advanced_params: Record<string, string | number>;
  actions: string[];
}

export interface ScenarioResultMetrics {
  affected_population_estimate: number;
  best_travel_time_minutes: number | null;
  best_route_label: string;
  estimated_emergency_response_minutes: number;
  cascade_narrative: string[];
}

export interface ScenarioResult {
  scenario_id: string;
  computed_at: string;
  baseline: ScenarioResultMetrics;
  with_actions: ScenarioResultMetrics;
  delta: {
    affected_population_change: number;
    travel_time_change_minutes: number | null;
    emergency_response_change_minutes: number;
    actions_tested: string[];
    estimated_cost_usd: number;
  };
  assumptions: string[];
  uncertainty_notes: string[];
  method: string;
}

export interface HiddenRisk {
  risk_id: string;
  category: string;
  title: string;
  detail: string;
  evidence: string[];
  severity_rank: number;
}

export interface SourceStatus {
  key: string;
  display_name: string;
  organization: string;
  status: DataStatus;
  detail: string;
  checked_at: string;
}

export interface ModelCard {
  model_id: string;
  version: string;
  display_name: string;
  purpose: string;
  method: string;
  inputs: string[];
  outputs: string[];
  known_limitations: string[];
  validation_status: string;
  not_intended_for: string[];
}

export interface AssistantSource {
  label: string;
  url?: string | null;
}

export interface AssistantContext {
  scope: "regional" | "global";
  selected_global_event_id?: string | null;
  horizon_minutes?: number | null;
}

export interface MapAction {
  action: string;
  target_id?: string | null;
}

export interface AssistantToolCall {
  tool: string;
  status: string;
  summary: string;
}

export interface AssistantAnswer {
  answer: string;
  time_range: TimeRange;
  location_label?: string | null;
  sources: AssistantSource[];
  observed_vs_inferred: string[];
  confidence: Confidence;
  limitations: string[];
  map_actions: MapAction[];
  tool_trace: AssistantToolCall[];
  suggested_questions: string[];
  generated_at: string;
  prose_source: string;
}

export interface PortfolioValidationIssue {
  row_number?: number | null;
  field?: string | null;
  issue: string;
}

export interface PortfolioExposure {
  portfolio_id: string;
  asset_count: number;
  valid_asset_count: number;
  assets_in_active_alert: number;
  accumulation_hotspot_note: string;
  missing_value_count: number;
  validation_issues: PortfolioValidationIssue[];
  disclaimer: string;
}

export interface HazardEvent {
  id: string;
  event_id: string;
  hazard_type: string;
  headline: string;
  description: string;
  severity: Severity;
  certainty: CertaintyClass;
  observed_at: string;
  updated_at: string;
  geometry: Geometry;
  measurements: Record<string, number>;
}

export interface Alert {
  id: string;
  alert_id: string;
  hazard_type: string;
  headline: string;
  description: string;
  severity: Severity;
  certainty: CertaintyClass;
  effective_at: string;
  expires_at?: string | null;
  geometry: Geometry;
  area_description?: string | null;
}

export interface SensorObservation {
  id: string;
  sensor_id: string;
  sensor_name: string;
  sensor_type: string;
  geometry: Geometry;
  observed_at: string;
  value: number;
  unit: string;
  trend_per_hour?: number | null;
  is_anomalous: boolean;
}

export interface LiveEventsResponse {
  events: HazardEvent[];
  alerts: Alert[];
  sensors: SensorObservation[];
  generated_at: string;
}

export interface NewsArticle {
  article_id: string;
  title: string;
  url: string;
  publisher_domain: string;
  source_country?: string | null;
  language?: string | null;
  published_at: string;
}

export interface NewsArticlesResponse {
  articles: NewsArticle[];
  data_status: DataStatus;
  retrieved_at: string;
  query_label: string;
  hazard_filter: "all" | "flood" | "wildfire" | "earthquake" | "storm" | "drought" | "cat_model" | "resilience";
  hours: number;
  source_name: string;
  source_url: string;
  notice: string;
  error?: string | null;
}

export interface HazardSignalSummary {
  signal_id: string;
  hazard_type: string;
  label: string;
  source: string;
  source_url?: string | null;
  data_status: DataStatus;
  certainty: CertaintyClass;
  severity: Severity;
  center: [number, number];
  observed_at: string;
  detail: string;
}

export interface ConsequenceStep {
  step_id: string;
  label: string;
  detail: string;
  certainty: CertaintyClass;
  confidence: Confidence;
  time_window: string;
}

export interface EvidenceChannel {
  channel: string;
  agreement: "supports" | "partial" | "conflicts" | "unavailable";
  detail: string;
  data_status: DataStatus;
}

export interface PossibleFuture {
  future_id: string;
  label: string;
  support: "most_supported" | "plausible" | "stress_case";
  detail: string;
  consequence: string;
  distinguishing_signal: string;
}

export interface VerificationPriority {
  rank: number;
  label: string;
  why: string;
  expected_value: string;
  action: string;
}

export interface CompoundEventSummary {
  event_id: string;
  title: string;
  region_label: string;
  status: string;
  center: [number, number];
  hazards: string[];
  data_status: DataStatus;
  is_demo: boolean;
  fusion_confidence: Confidence;
  fusion_explanation: string;
  matched_on: string[];
  signals: HazardSignalSummary[];
  consequence_chain: ConsequenceStep[];
  possible_futures: PossibleFuture[];
  evidence_agreement: EvidenceChannel[];
  next_checks: VerificationPriority[];
  limitations: string[];
}

export interface MultiHazardOverview {
  generated_at: string;
  live_feed_count: number;
  demo_feed_count: number;
  unavailable_feed_count: number;
  compound_events: CompoundEventSummary[];
  research_notice: string;
}

export interface CommunityReport {
  report_id: string;
  posted_at: string;
  channel: string;
  text: string;
  location_label: string;
  center: [number, number];
  sentiment: "alarmed" | "concerned" | "seeking_info" | "calm" | "relieved" | string;
  theme: string;
  certainty: "user_reported" | "unverified" | string;
  corroboration: "corroborated" | "uncorroborated" | "conflicts" | string;
  corroboration_detail: string;
}

export interface SentimentBucket {
  sentiment: string;
  label: string;
  count: number;
  share: number;
}

export interface ThemeCluster {
  theme: string;
  label: string;
  count: number;
  dominant_sentiment: string;
  example: string;
  corroboration_note: string;
}

export interface ConcernIndex {
  score: number;
  band: "calm" | "watchful" | "concerned" | "alarmed" | string;
  band_label: string;
  trend: "rising" | "steady" | "easing" | string;
  trend_detail: string;
  method: string;
}

export interface CorroborationSummary {
  corroborated: number;
  uncorroborated: number;
  conflicts: number;
  note: string;
}

export interface CommunityPulseResponse {
  incident_id: string;
  region_label: string;
  window_label: string;
  generated_at: string;
  data_status: DataStatus;
  is_demo: boolean;
  total_reports: number;
  concern_index: ConcernIndex;
  sentiment_breakdown: SentimentBucket[];
  theme_clusters: ThemeCluster[];
  corroboration: CorroborationSummary;
  reports: CommunityReport[];
  limitations: string[];
  responsible_use: string[];
}

export type Mode = "live" | "replay";
