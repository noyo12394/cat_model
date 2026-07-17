"""Response models for unverified community-language signals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.enums import DataStatus


class CommunitySignal(BaseModel):
    post_id: str
    text: str
    observed_at: datetime
    language: str | None = None
    tone: Literal["urgent_language", "concern_language", "neutral_language"]
    report_type: Literal["possible_impact_report", "possible_condition_report", "event_mention"]
    tags: list[str] = Field(default_factory=list)
    source_url: HttpUrl
    certainty_class: Literal["user_reported"] = "user_reported"
    verification_status: Literal["unverified"] = "unverified"


class CommunitySignalsResponse(BaseModel):
    event_id: str
    event_name: str
    event_center: tuple[float, float]
    availability: Literal["available", "unavailable"]
    availability_label: str
    availability_detail: str
    generated_at: datetime
    data_status: DataStatus
    items: list[CommunitySignal] = Field(default_factory=list)
    source_name: str = "X API recent search"
    source_url: HttpUrl = "https://docs.x.com/x-api/posts/search-recent-posts"
    method: str = "Deterministic language tags over source-returned public posts"
    limitations: list[str] = Field(default_factory=lambda: [
        "Posts are unverified user reports. They never change an official alert level, model forecast, or risk score.",
        "EarthPulse does not infer a poster's location from profile metadata or text. A post is associated only with the selected official event query.",
        "Language cues are transparent labels, not a measure of truth, sentiment certainty, or population impact.",
    ])
    error: str | None = None
