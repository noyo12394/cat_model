"""Facilities, routes and infrastructure dependencies (impact systems)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import BaseRecord, Geometry
from app.schemas.enums import FacilityType, OperationalState


class Facility(BaseRecord):
    facility_id: str
    facility_type: FacilityType
    name: str
    geometry: Geometry
    operational_state: OperationalState = OperationalState.UNKNOWN
    attributes: dict[str, str | float | int | bool | None] = Field(default_factory=dict)
    data_completeness: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Share of expected attributes that are known."
    )
    backup_power: Optional[bool] = None
    served_population: Optional[int] = None


class RouteSegmentExposure(BaseModel):
    segment_id: str
    description: str
    hazard_overlap: bool
    hazard_labels: list[str] = Field(default_factory=list)
    river_crossing: bool = False
    reported_closure: bool = False


class RouteOption(BaseModel):
    route_id: str
    label: str
    duration_minutes: Optional[float] = None
    distance_km: Optional[float] = None
    geometry: Geometry
    exposure_note: str = Field(
        description='Plain language e.g. "Lower current hazard exposure" - never "safe".'
    )
    exposure_level: str = Field(description="lower | elevated | unavailable")
    segments: list[RouteSegmentExposure] = Field(default_factory=list)
    data_freshness_minutes: Optional[float] = None
    confidence: str = "moderate"


class InfrastructureDependency(BaseRecord):
    dependency_id: str
    from_facility_id: str
    to_facility_id: str
    relationship: str = Field(
        description='e.g. "depends_on", "provides_access_to", "upstream_of", "supplies"'
    )
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    is_uncertain: bool = False
