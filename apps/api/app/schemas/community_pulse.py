"""Schemas for community-signal sentiment analysis ("Community Pulse").

Community Pulse is deliberately *social sensing*, not an official indicator. It
aggregates short community reports into a transparent, deterministic picture of
public concern. Two guardrails are baked into the shapes here:

* Every report carries a ``certainty`` of ``user_reported`` or ``unverified`` -
  never ``observed`` or ``official_alert`` - so the UI can never present crowd
  mood as a confirmed fact (product principle 2.2).
* The concern index is a *counted* aggregate. Sentiment and theme tags are
  categorical inputs; the score is a weighted count, not a number invented by a
  language model (principle "do not use an LLM to calculate numerical
  outcomes", section 31).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import CertaintyClass, DataStatus


class CommunityReport(BaseModel):
    report_id: str
    posted_at: datetime
    channel: str  # e.g. "Community app", "Public social post", "Info hotline"
    text: str
    location_label: str
    center: tuple[float, float]
    sentiment: str  # alarmed | concerned | seeking_info | calm | relieved
    theme: str  # access | power | water_level | evacuation | assistance | rumor
    certainty: CertaintyClass  # user_reported | unverified only
    corroboration: str  # corroborated | uncorroborated | conflicts
    corroboration_detail: str


class SentimentBucket(BaseModel):
    sentiment: str
    label: str
    count: int
    share: float  # count / total, rounded - a deterministic proportion


class ThemeCluster(BaseModel):
    theme: str
    label: str
    count: int
    dominant_sentiment: str
    example: str
    corroboration_note: str


class ConcernIndex(BaseModel):
    score: float  # 0..1, weighted count of sentiment tags
    band: str  # calm | watchful | concerned | alarmed
    band_label: str
    trend: str  # rising | steady | easing
    trend_detail: str
    method: str


class CorroborationSummary(BaseModel):
    corroborated: int
    uncorroborated: int
    conflicts: int
    note: str


class CommunityPulseResponse(BaseModel):
    incident_id: str
    region_label: str
    window_label: str
    generated_at: datetime
    data_status: DataStatus
    is_demo: bool
    total_reports: int
    concern_index: ConcernIndex
    sentiment_breakdown: list[SentimentBucket]
    theme_clusters: list[ThemeCluster]
    corroboration: CorroborationSummary
    reports: list[CommunityReport]
    limitations: list[str]
    responsible_use: list[str]
