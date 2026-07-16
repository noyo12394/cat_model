"""Schemas for explainable multi-hazard and compound-impact intelligence."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import CertaintyClass, Confidence, DataStatus, Severity


class HazardSignalSummary(BaseModel):
    signal_id: str
    hazard_type: str
    label: str
    source: str
    source_url: str | None = None
    data_status: DataStatus
    certainty: CertaintyClass
    severity: Severity
    center: tuple[float, float]
    observed_at: datetime
    detail: str


class ConsequenceStep(BaseModel):
    step_id: str
    label: str
    detail: str
    certainty: CertaintyClass
    confidence: Confidence
    time_window: str


class EvidenceChannel(BaseModel):
    channel: str
    agreement: str  # supports | partial | conflicts | unavailable
    detail: str
    data_status: DataStatus


class PossibleFuture(BaseModel):
    future_id: str
    label: str
    support: str  # most_supported | plausible | stress_case
    detail: str
    consequence: str
    distinguishing_signal: str


class VerificationPriority(BaseModel):
    rank: int
    label: str
    why: str
    expected_value: str
    action: str


class CompoundEventSummary(BaseModel):
    event_id: str
    title: str
    region_label: str
    status: str
    center: tuple[float, float]
    hazards: list[str]
    data_status: DataStatus
    is_demo: bool
    fusion_confidence: Confidence
    fusion_explanation: str
    matched_on: list[str]
    signals: list[HazardSignalSummary]
    consequence_chain: list[ConsequenceStep]
    possible_futures: list[PossibleFuture]
    evidence_agreement: list[EvidenceChannel]
    next_checks: list[VerificationPriority]
    limitations: list[str]


class MultiHazardOverview(BaseModel):
    generated_at: datetime
    live_feed_count: int
    demo_feed_count: int
    unavailable_feed_count: int
    compound_events: list[CompoundEventSummary]
    research_notice: str
