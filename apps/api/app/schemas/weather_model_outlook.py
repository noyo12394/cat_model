"""Schemas for source-bounded, point-level weather-model guidance."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.enums import DataStatus


class ModelWeatherMetric(BaseModel):
    """One directly reported atmospheric variable, never a fabricated hazard score."""

    key: str
    label: str
    value: float
    unit: str
    range_low: float | None = None
    range_high: float | None = None
    detail: str | None = None


class ModelWeatherOutlookResponse(BaseModel):
    target_at: datetime
    horizon_hours: float
    availability: Literal["available", "unavailable"]
    availability_label: str
    availability_detail: str
    coverage_type: Literal["short_range_ml", "short_range_numerical", "seasonal_ensemble", "unavailable"]
    location_name: str
    center: tuple[float, float]
    provider: str = "Open-Meteo"
    model_name: str | None = None
    source_url: HttpUrl = "https://open-meteo.com/en/docs"
    generated_at: datetime
    data_status: DataStatus
    metrics: list[ModelWeatherMetric] = Field(default_factory=list)
    reliability_note: str
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None
