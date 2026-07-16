"""Grounded AI Assistant request/response schemas (section 31.8)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimeRange
from app.schemas.enums import Confidence


class AssistantQuery(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AssistantSource(BaseModel):
    label: str
    url: str | None = None


class MapAction(BaseModel):
    action: str = Field(description='e.g. "focus_incident", "filter_layer", "focus_place"')
    target_id: str | None = None


class AssistantAnswer(BaseModel):
    answer: str
    time_range: TimeRange
    location_label: str | None = None
    sources: list[AssistantSource] = Field(default_factory=list)
    observed_vs_inferred: list[str] = Field(
        default_factory=list, description="Plain-language labels distinguishing fact from inference."
    )
    confidence: Confidence
    limitations: list[str] = Field(default_factory=list)
    map_actions: list[MapAction] = Field(default_factory=list)
    generated_at: datetime
    prose_source: str = Field(
        default="rule-based",
        description='"rule-based" or "llm-polished" - see services/assistant.py',
    )
