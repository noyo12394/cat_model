"""Transparent short-horizon operational triage for global GDACS events.

This is deliberately *not* a hazard-probability forecast. It ranks which
official events deserve verification in the selected operating window using
the alert metadata that GDACS already publishes.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.enums import DataStatus


class GlobalWatchItem(BaseModel):
    event_id: str
    name: str
    event_type: str
    country: str
    center: tuple[float, float]
    alert_level: str
    alert_score: float | None = None
    modified_at: datetime
    priority_score: int = Field(ge=0, le=100)
    priority_label: str
    drivers: list[str] = Field(default_factory=list)
    next_action: str
    report_url: HttpUrl


class GlobalOutlookResponse(BaseModel):
    horizon_minutes: int = Field(ge=0, le=1440)
    horizon_label: str
    generated_at: datetime
    data_status: DataStatus
    source_updated_at: datetime | None = None
    method: str = "Transparent operational watch-priority calculation"
    method_detail: str = (
        "Ranks verification priority from the published GDACS alert level, alert score, and time since the event was modified. "
        "It does not predict hazard evolution, impact probability, or affected area."
    )
    items: list[GlobalWatchItem] = Field(default_factory=list)
    source_name: str = "Global Disaster Awareness and Coordination System (GDACS)"
    source_url: HttpUrl = "https://www.gdacs.org/"
    attribution: str = "Global Disaster Awareness and Coordination System, GDACS"
    limitations: list[str] = Field(default_factory=lambda: [
        "GDACS event and impact information is indicative and must be cross-checked with national authorities.",
        "This lens is a triage aid, not a calibrated forecast or emergency warning.",
    ])
    error: str | None = None
