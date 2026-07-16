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
    forecast_valid_from: datetime
    forecast_valid_to: datetime
    selected_point_at: datetime
    selected_point_center: tuple[float, float]
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
        "Forecast positions come from the nearest published NHC advisory point and must be read with the official forecast cone and advisory text.",
    ])
    error: str | None = None
