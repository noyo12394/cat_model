"""Normalized operational event records from the GDACS multi-hazard feed."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.enums import DataStatus


class GlobalEvent(BaseModel):
    event_id: str
    event_type: str
    name: str
    country: str
    alert_level: str
    alert_score: float | None = None
    severity_text: str
    from_date: datetime
    to_date: datetime
    modified_at: datetime
    center: tuple[float, float]
    source: str
    report_url: HttpUrl
    geometry_url: HttpUrl | None = None
    is_current: bool = True
    data_status: DataStatus = DataStatus.LIVE


class GlobalEventCounts(BaseModel):
    total: int = 0
    red: int = 0
    orange: int = 0
    green: int = 0


class GlobalEventsResponse(BaseModel):
    events: list[GlobalEvent] = Field(default_factory=list)
    counts: GlobalEventCounts = Field(default_factory=GlobalEventCounts)
    fetched_at: datetime
    source_updated_at: datetime | None = None
    source_name: str = "Global Disaster Alert and Coordination System (GDACS)"
    source_url: HttpUrl = "https://www.gdacs.org/"
    attribution: str = "Global Disaster Awareness and Coordination System, GDACS"
    standards: list[str] = Field(default_factory=lambda: ["GeoJSON", "GDACS MHEWS API"])
    data_status: DataStatus
    stale: bool = False
    result_cap: int = 500
    possibly_truncated: bool = False
    notice: str = (
        "GDACS impact estimates are indicative. Confirm critical decisions with national authorities "
        "and additional authoritative sources."
    )
    error: str | None = None
