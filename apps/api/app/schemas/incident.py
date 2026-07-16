"""Incident Room schema - the fused, evolving event (section 9 + 31.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import EvidenceTrail, Geometry
from app.schemas.enums import Confidence, HazardType, Severity


class TimelineEntry(BaseModel):
    entry_id: str
    at: datetime
    label: str
    detail: str
    certainty_class: str
    source: str
    is_first_detection: bool = False
    is_peak: bool = False
    is_recovery: bool = False


class IncidentSummary(BaseModel):
    incident_id: str
    slug: str
    title: str
    hazard_type: HazardType
    severity: Severity
    status: str = Field(description='"developing" | "active" | "recovering" | "resolved"')
    region_label: str
    center: tuple[float, float]
    geometry: Optional[Geometry] = None
    created_at: datetime
    updated_at: datetime
    overall_confidence: Confidence
    one_line_summary: str
    related_signal_count: int
    is_demo: bool = False


class FusionReason(BaseModel):
    """Why signals were grouped into one incident (section 31.1 output)."""

    incident_id: str
    matched_on: list[str]
    match_confidence: Confidence
    related_signal_ids: list[str]
    explanation: str


class WhatChangedItem(BaseModel):
    label: str
    detail: str
    certainty_class: str
    magnitude: Optional[float] = None
    unit: Optional[str] = None


class WhatChanged(BaseModel):
    incident_id: str
    compared_to_label: str
    compared_to_at: datetime
    now_at: datetime
    changes: list[WhatChangedItem]


class IncidentDetail(IncidentSummary):
    description: str
    timeline: list[TimelineEntry] = Field(default_factory=list)
    fusion_reason: Optional[FusionReason] = None
    affected_facility_ids: list[str] = Field(default_factory=list)
    affected_population_estimate: Optional[int] = None
    affected_population_note: str = (
        "Estimated from public population and facility-service data; treat as an "
        "order-of-magnitude figure, not a precise count."
    )
    sources: list[str] = Field(default_factory=list)
