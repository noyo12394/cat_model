"""Location Capsule response schema (section 8)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import Confidence


class NearbyCondition(BaseModel):
    label: str
    certainty_class: str
    detail: Optional[str] = None


class CriticalConnection(BaseModel):
    facility_id: str
    facility_type: str
    name: str
    distance_km: float
    travel_time_minutes: Optional[float] = None


class LocationCapsule(BaseModel):
    place_id: str
    name: str
    center: tuple[float, float]
    current_status_headline: str
    nearby_conditions: list[NearbyCondition] = Field(default_factory=list)
    next_24h_notes: list[str] = Field(default_factory=list)
    forecast_confidence: Confidence
    critical_connections: list[CriticalConnection] = Field(default_factory=list)
    data_confidence: Confidence
    last_updated: datetime
    active_incident_ids: list[str] = Field(default_factory=list)
    is_demo: bool = False
