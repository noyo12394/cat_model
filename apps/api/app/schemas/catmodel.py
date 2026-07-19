"""Catastrophe-modelling schemas (RiskChain deliverable 7 / 9).

These types implement the transparent CAT calculation chain

    Hazard -> Exposure -> Vulnerability -> Damage -> Financial
           -> Probabilistic -> Uncertainty -> Audit -> Reporting

with the master prompt's non-negotiables encoded in the shapes themselves:

* Every exposure attribute carries an ``AttributeOrigin`` so an inferred value
  can never be rendered as observed (rule 11).
* Losses are ranges with a distribution, never a single false-precise number
  (principle 2.3).
* Vulnerability functions carry a calibration range and applicability notes, and
  damage results flag when an asset's hazard intensity falls outside that range
  (extrapolation), rather than silently extrapolating.
* Probabilistic results separate a *return-period event* from a *return-period
  loss* and state their independence/occurrence assumptions (rules 9, and the
  OEP-vs-AEP distinction in section 10.5).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import Provenance
from app.schemas.enums import Confidence, DataStatus


class AttributeOrigin(str, Enum):
    """Where a single exposure attribute came from (section 10.2)."""

    OBSERVED = "observed"
    USER_SUPPLIED = "user_supplied"
    PUBLIC_RECORD = "public_record"
    LICENSED = "licensed"
    MODEL_INFERRED = "model_inferred"
    DEFAULT_ASSUMPTION = "default_assumption"
    MISSING = "missing"


class DamageState(str, Enum):
    NONE = "none"
    SLIGHT = "slight"
    MODERATE = "moderate"
    EXTENSIVE = "extensive"
    COMPLETE = "complete"


class ApprovalStatus(str, Enum):
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    UNDER_REVIEW = "under_review"
    APPROVED_EXPERIMENTAL = "approved_for_experimentation"
    APPROVED_PRODUCTION = "approved_for_production"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


# --- Hazard -----------------------------------------------------------------

class IntensityMeasure(BaseModel):
    name: str  # e.g. "flood_depth"
    label: str  # e.g. "Flood depth above grade"
    unit: str  # e.g. "ft"


class AssetHazardIntensity(BaseModel):
    asset_id: str
    intensity: float
    unit: str
    origin: AttributeOrigin


# --- Exposure ---------------------------------------------------------------

class ExposureAsset(BaseModel):
    asset_id: str
    name: str
    center: tuple[float, float]
    occupancy: str  # residential | commercial | industrial | hospital | ...
    construction: str  # wood_frame | masonry | steel | reinforced_concrete | unknown
    number_of_storeys: int
    year_built: int | None = None
    first_floor_elevation_ft: float | None = None
    floor_area_sqft: float
    replacement_value_usd: float
    contents_value_usd: float
    business_interruption_daily_usd: float
    criticality: str = "standard"  # standard | important | critical
    # Per-attribute origin flags. Keys are field names above.
    attribute_origins: dict[str, AttributeOrigin]


# --- Vulnerability ----------------------------------------------------------

class DepthDamagePoint(BaseModel):
    intensity: float  # e.g. flood depth in ft (may be negative below grade)
    mean_damage_ratio: float = Field(ge=0.0, le=1.0)


class VulnerabilityFunction(BaseModel):
    function_id: str
    name: str
    hazard: str
    asset_class: str  # occupancy this curve applies to
    intensity_measure: IntensityMeasure
    curve: list[DepthDamagePoint]  # monotonic non-decreasing in intensity
    calibration_min: float
    calibration_max: float
    # Coefficient of variation of the damage ratio (secondary uncertainty).
    damage_ratio_cov: float = Field(ge=0.0)
    source: Provenance
    applicability_notes: str
    prohibited_extrapolations: str
    version: str
    approval_status: ApprovalStatus


# --- Damage & financial -----------------------------------------------------

class AssetDamageResult(BaseModel):
    asset_id: str
    intensity: float
    mean_damage_ratio: float
    damage_state_probabilities: dict[str, float]
    building_loss_usd: float
    contents_loss_usd: float
    business_interruption_loss_usd: float
    ground_up_loss_usd: float
    extrapolated: bool
    vulnerability_function_id: str


class FinancialTerms(BaseModel):
    deductible_usd: float = Field(default=0.0, ge=0.0)
    limit_usd: float | None = Field(default=None, ge=0.0)
    coinsurance: float = Field(default=1.0, ge=0.0, le=1.0)  # insurer share
    currency: str = "USD"


class AssetFinancialResult(BaseModel):
    asset_id: str
    ground_up_loss_usd: float
    deductible_applied_usd: float
    gross_loss_usd: float  # after deductible and limit
    net_insured_loss_usd: float  # after coinsurance
    currency: str


class LossDistribution(BaseModel):
    mean_usd: float
    p10_usd: float
    p50_usd: float
    p90_usd: float
    range_low_usd: float
    range_high_usd: float
    std_usd: float
    samples: int
    method: str


# --- Audit & manifest -------------------------------------------------------

class ModelAuditFinding(BaseModel):
    code: str
    severity: str  # info | warning | high
    title: str
    detail: str
    recommendation: str


class Assumption(BaseModel):
    label: str
    value: str
    origin: AttributeOrigin


class ResolutionBadge(BaseModel):
    analysis_resolution: str
    hazard_resolution: str
    population_resolution: str
    building_use_origin: AttributeOrigin


class ConfidenceAssessment(BaseModel):
    band: Confidence
    drivers: list[str]  # the specific reasons behind the band
    largest_uncertainty: str


class ModelRunManifest(BaseModel):
    run_id: str
    created_at: datetime
    code_version: str
    model_ids: dict[str, str]  # role -> "id@version"
    random_seed: int
    parameters: dict[str, float | int | str]
    input_summary: dict[str, float | int | str]
    parent_run_id: str | None = None


# --- Top-level run result ---------------------------------------------------

class CatModelRunResult(BaseModel):
    run_id: str
    scenario_label: str
    hazard_type: str
    region_label: str
    is_demo: bool
    data_status: DataStatus
    resolution: ResolutionBadge
    asset_count: int
    financial_terms: FinancialTerms
    # Aggregate ground-up (economic) loss.
    ground_up_distribution: LossDistribution
    # Aggregate insured loss after financial terms.
    gross_distribution: LossDistribution
    net_insured_distribution: LossDistribution
    asset_damage: list[AssetDamageResult]
    asset_financial: list[AssetFinancialResult]
    confidence: ConfidenceAssessment
    audit_findings: list[ModelAuditFinding]
    assumptions: list[Assumption]
    sources: list[Provenance]
    limitations: list[str]
    manifest: ModelRunManifest


# --- Probabilistic ----------------------------------------------------------

class EventDefinition(BaseModel):
    event_id: str
    name: str
    annual_rate: float = Field(gt=0.0)  # lambda_e (expected occurrences/yr)
    mean_ground_up_usd: float = Field(ge=0.0)
    loss_cov: float = Field(ge=0.0)
    return_period_years: float  # of the *event*, = 1/rate


class EPCurvePoint(BaseModel):
    return_period_years: float
    exceedance_probability: float
    loss_usd: float


class QuantileLoss(BaseModel):
    quantile: float
    loss_usd: float


class ProbabilisticResult(BaseModel):
    basis: str  # "ground_up" | "gross"
    aal_usd: float
    event_count: int
    simulation_years: int
    oep_curve: list[EPCurvePoint]  # largest single event loss per year
    aep_curve: list[EPCurvePoint]  # aggregate loss per year
    var: list[QuantileLoss]
    tvar: list[QuantileLoss]
    method: str
    assumptions: list[str]
    limitations: list[str]


# --- Mitigation -------------------------------------------------------------

class MitigationOption(BaseModel):
    option_id: str
    name: str
    description: str
    cost_usd: float
    applies_to_occupancy: list[str]
    mechanism: str  # human-readable description of the modelled effect
    supported_by_model: bool


class MitigationResult(BaseModel):
    option_id: str
    name: str
    baseline_median_usd: float
    with_mitigation_median_usd: float
    avoided_loss_usd: float
    cost_usd: float
    benefit_cost_ratio: float | None
    confidence: Confidence
    assumptions: list[str]
    caveat: str


# --- Registry / model card --------------------------------------------------

class ModelRegistryEntry(BaseModel):
    model_id: str
    name: str
    provider: str
    hazard: str
    geography: str
    geographic_resolution: str
    asset_classes: list[str]
    intensity_measure: str
    outputs: list[str]
    version: str
    calibration_dataset: str
    validation_geography: str
    peer_reviewed_source: str | None
    doi: str | None
    known_limitations: list[str]
    approval_status: ApprovalStatus
    not_intended_for: list[str]


# --- Operational API contracts ---------------------------------------------

class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ModelRunJob(BaseModel):
    """Long-running-model contract, executed inline only in the demo runtime.

    The shape is queue-compatible, but ``execution_mode`` prevents the Vercel
    demonstration from pretending it has a durable worker when it does not.
    """

    job_id: str
    state: JobState
    progress_percent: int = Field(ge=0, le=100)
    submitted_at: datetime
    completed_at: datetime | None = None
    execution_mode: Literal["inline_demo", "background_worker"]
    run_id: str | None = None
    error: str | None = None
    limitations: list[str] = Field(default_factory=list)


class RunComparisonMetric(BaseModel):
    metric: str
    baseline_value: float
    comparison_value: float
    absolute_change: float
    percent_change: float | None
    unit: str


class ModelRunComparison(BaseModel):
    baseline_run_id: str
    comparison_run_id: str
    metrics: list[RunComparisonMetric]
    changed_assumptions: list[str]
    interpretation: list[str]
    limitations: list[str]


class ModelResultLayer(BaseModel):
    run_id: str
    layer_id: str
    title: str
    geometry_type: str
    data_status: DataStatus
    geojson: dict[str, Any]
    value_field: str
    value_unit: str
    provenance_note: str
    limitations: list[str]


class ReportSection(BaseModel):
    section_id: str
    title: str
    statements: list[str]
    data_references: list[str] = Field(default_factory=list)


class StructuredRunReport(BaseModel):
    report_id: str
    run_id: str
    report_type: Literal["executive", "technical", "underwriting", "public"]
    generated_at: datetime
    title: str
    sections: list[ReportSection]
    citations: list[Provenance]
    manifest: ModelRunManifest
    limitations: list[str]


class DataCoverageItem(BaseModel):
    layer_id: str
    label: str
    availability: Literal["available_demo", "available_live", "unavailable"]
    use_in_run: str
    source: str
    geographic_resolution: str
    temporal_resolution: str
    attribute_origin: AttributeOrigin
    limitations: list[str]


class CapabilityStatus(BaseModel):
    deliverable: str
    status: Literal["implemented", "partial", "not_started"]
    evidence: list[str]
    next_gap: str | None = None


class CapabilityCoverage(BaseModel):
    implemented: int
    partial: int
    not_started: int
    total: int
    capabilities: list[CapabilityStatus]
