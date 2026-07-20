"""Runtime contracts that keep screening separate from loss estimation."""
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

class AnalysisMode(str, Enum):
    LIVE = "live"
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"
    DEMO = "demo"

class AnalysisHazard(str, Enum):
    HURRICANE = "hurricane"
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    WILDFIRE = "wildfire"

class HazardEventSummary(BaseModel):
    provider: str
    provider_event_id: str
    hazard_type: AnalysisHazard
    name: str
    status: str
    start_time: datetime | None = None
    update_time: datetime | None = None
    center: tuple[float, float] | None = None
    source_url: str
    source_version: str
    classification: Literal["observed", "forecast", "scenario"]
    advisory_id: str | None = None
    footprint_available: bool = False
    limitations: list[str] = Field(default_factory=list)

class HazardEventSearchResponse(BaseModel):
    events: list[HazardEventSummary]
    provider: str
    retrieved_at: datetime
    data_status: Literal["live", "unavailable"]
    message: str | None = None

class AnalysisLocation(BaseModel):
    place_id: str
    name: str
    center: tuple[float, float]
    bbox: tuple[float, float, float, float] | None = None
    state: str | None = None
    state_fips: str | None = None
    county: str | None = None
    county_fips: str | None = None
    tract: str | None = None
    tract_geoid: str | None = None
    geography_vintage: str | None = None

class AnalysisRunRequest(BaseModel):
    mode: AnalysisMode
    hazard_type: AnalysisHazard
    location: AnalysisLocation | None = None
    provider: str | None = None
    event_id: str | None = None
    advisory_id: str | None = None
    threshold: str | None = None
    return_period_years: int | None = Field(default=None, ge=2, le=10_000)
    start_date: date | None = None
    end_date: date | None = None
    exposure_dataset: str = "USACE NSI 2026 Base"
    vulnerability_model: str | None = None
    exposure_reference: Literal["event_time", "current"] = "current"
    simulation_count: int = Field(default=1000, ge=200, le=5000)
    seed: int = 12345

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> "AnalysisRunRequest":
        if self.mode == AnalysisMode.HYPOTHETICAL and self.location is None:
            raise ValueError("A resolved location is required for a hypothetical scenario")
        if self.mode in {AnalysisMode.LIVE, AnalysisMode.HISTORICAL} and not self.event_id:
            raise ValueError("An authoritative event is required for this mode")
        if self.hazard_type == AnalysisHazard.FLOOD and self.mode == AnalysisMode.HYPOTHETICAL and not self.return_period_years:
            raise ValueError("A return period is required for a hypothetical flood scenario")
        return self

class SourceRecord(BaseModel):
    dataset: str
    provider: str
    url: str
    version: str
    retrieved_at: datetime
    data_timestamp: datetime | None = None
    status: Literal["loaded", "unavailable", "not_applicable"]
    note: str | None = None

class AnalysisTotals(BaseModel):
    structures: int | None = None
    population: int | None = None
    structure_value_usd: float | None = None
    contents_value_usd: float | None = None
    valid_assets: int = 0
    excluded_assets: int = 0

class AnalysisManifest(BaseModel):
    run_id: str
    created_at: datetime
    code_version: str
    inputs: dict[str, Any]
    provider_event_ids: dict[str, str]
    advisory_versions: list[str]
    geographic_boundaries: dict[str, Any]
    sources: list[SourceRecord]
    vulnerability_function_ids: list[str]
    assumptions: list[str]
    missing_fields: list[str]
    excluded_records: dict[str, int]
    simulation_seed: int
    simulation_count: int
    calculation_summary: str

class AnalysisRunResult(BaseModel):
    run_id: str
    result_type: Literal["exposure_screening", "loss_estimate"]
    mode: AnalysisMode
    hazard_type: AnalysisHazard
    title: str
    provider_event_id: str | None = None
    event_time: datetime | None = None
    analysis_time: datetime
    geography: AnalysisLocation | None = None
    hazard_threshold: str | None = None
    hazard_layers: list[dict[str, Any]] = Field(default_factory=list)
    totals: AnalysisTotals
    confidence: dict[str, Any]
    component_status: dict[str, str]
    limitations: list[str]
    loss: dict[str, Any] | None = None
    manifest: AnalysisManifest
