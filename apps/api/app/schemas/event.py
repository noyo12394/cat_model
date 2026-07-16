"""Normalized hazard event - the schema from section 33 of the spec."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import BaseRecord, Geometry
from app.schemas.enums import CertaintyClass, HazardType, Severity, Urgency


class HazardEvent(BaseRecord):
    event_id: str
    hazard_type: HazardType
    status: CertaintyClass
    headline: str
    description: str
    severity: Severity
    certainty: CertaintyClass
    urgency: Urgency
    observed_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    geometry: Geometry
    measurements: dict[str, float] = Field(default_factory=dict)


class SensorObservation(BaseRecord):
    sensor_id: str
    sensor_name: str
    sensor_type: str = Field(description='e.g. "river_gauge", "air_quality_monitor"')
    geometry: Geometry
    observed_at: datetime
    value: float
    unit: str
    trend_per_hour: Optional[float] = None
    is_anomalous: bool = False
    anomaly_reason: Optional[str] = None


class Forecast(BaseRecord):
    forecast_id: str
    hazard_type: HazardType
    issued_at: datetime
    valid_from: datetime
    valid_to: datetime
    geometry: Geometry
    headline: str
    detail: str
    confidence_note: Optional[str] = None


class Alert(BaseRecord):
    alert_id: str
    hazard_type: HazardType
    headline: str
    description: str
    severity: Severity
    certainty: CertaintyClass
    urgency: Urgency
    effective_at: datetime
    expires_at: Optional[datetime] = None
    geometry: Geometry
    area_description: Optional[str] = None
