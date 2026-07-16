"""Provenance and evidence primitives shared by every schema.

Product principle 2.3 requires that "every important statement needs
evidence": source, source organization, observation time, retrieval time,
model version, inputs used, confidence and known limitations. ``Provenance``
and ``EvidenceTrail`` below are embedded in every record that makes a claim.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.enums import CertaintyClass, Confidence, DataStatus, SourceName


class GeoPoint(BaseModel):
    type: str = Field(default="Point", frozen=True)
    coordinates: tuple[float, float] = Field(
        ..., description="[longitude, latitude] per GeoJSON convention"
    )


class GeoPolygon(BaseModel):
    type: str = Field(default="Polygon", frozen=True)
    coordinates: list[list[tuple[float, float]]]


class GeoLineString(BaseModel):
    type: str = Field(default="LineString", frozen=True)
    coordinates: list[tuple[float, float]]


Geometry = GeoPoint | GeoPolygon | GeoLineString


class Provenance(BaseModel):
    """Where a fact came from and how fresh it is."""

    source: SourceName
    source_organization: str
    source_url: Optional[str] = None
    license: Optional[str] = None
    observed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    retrieved_at: datetime
    data_status: DataStatus = DataStatus.LIVE
    staleness_minutes: Optional[float] = Field(
        default=None, description="Minutes since the source last updated, if known."
    )


class ModelBasis(BaseModel):
    """The 'technical information' block of an evidence trail (section 23)."""

    model_id: str
    model_version: str
    run_at: datetime
    inputs_used: list[str] = Field(default_factory=list)
    confidence_method: str = Field(
        default="rule-based heuristic over official inputs; not a calibrated probability"
    )


class EvidenceItem(BaseModel):
    label: str
    detail: Optional[str] = None
    provenance: Optional[Provenance] = None


class EvidenceTrail(BaseModel):
    """Full lineage behind any prediction, warning or recommendation."""

    claim: str
    certainty_class: CertaintyClass
    confidence: Confidence
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Known limitations that should reduce trust in this claim.",
    )
    model_basis: Optional[ModelBasis] = None
    plain_language_summary: str


class TimeRange(BaseModel):
    start: datetime
    end: Optional[datetime] = None
    label: Optional[str] = Field(
        default=None, description='e.g. "Next 1-3 hours" - human phrasing, no false precision'
    )


class QualityFlag(str):
    """Free-form quality flag string, kept as a type alias for clarity."""


class BaseRecord(BaseModel):
    """Fields common to nearly every normalized record in the common data model."""

    id: str
    source_event_id: Optional[str] = None
    provenance: Provenance
    quality_flags: list[str] = Field(default_factory=list)
    raw_payload_reference: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)
