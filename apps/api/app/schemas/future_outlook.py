"""Response models for date-specific, officially published forecast coverage."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.enums import DataStatus


class FutureForecastEvent(BaseModel):
    event_id: str
    name: str
    event_type: Literal["TC"] = "TC"
    storm_type: str
    basin: str
    headline: str | None = None
    observed_at: datetime | None = None
    coverage_status: Literal["dated_track_point", "official_advisory"]
    forecast_valid_from: datetime | None = None
    forecast_valid_to: datetime | None = None
    selected_point_at: datetime | None = None
    selected_point_center: tuple[float, float] | None = None
    advisory_url: HttpUrl
    track_url: HttpUrl
    certainty_class: Literal["official_forecast"] = "official_forecast"


class FutureOutlookResponse(BaseModel):
    target_at: datetime
    horizon_hours: float
    availability: Literal["available", "unavailable"]
    availability_label: str
    availability_detail: str
    generated_at: datetime
    data_status: DataStatus
    items: list[FutureForecastEvent] = Field(default_factory=list)
    source_name: str = "NOAA National Hurricane Center"
    source_url: HttpUrl = "https://www.nhc.noaa.gov/gis/"
    attribution: str = "NOAA National Hurricane Center official forecast products"
    coverage: str = "Active named tropical cyclones in the Atlantic and eastern Pacific, up to five days when an official advisory track exists."
    limitations: list[str] = Field(default_factory=lambda: [
        "This is not a global all-hazard forecast: it does not predict earthquakes, floods, wildfires, or events that have not been issued by an authority.",
        "A map point appears only when the source supplies a dated forecast point; otherwise EarthPulse links to the official advisory without inferring a position.",
    ])
    error: str | None = None
