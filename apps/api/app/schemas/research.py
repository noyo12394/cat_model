"""Research & formula-discovery schemas (section 12).

The extraction schema mirrors section 12's required fields. Two honesty rules
are structural: a paper always carries a ``human_review_status`` and an
``extraction_performed`` flag, and nothing here promotes a formula into the
calculation engine — that only happens through the model registry after review.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ReviewStatus(str, Enum):
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    UNDER_REVIEW = "under_review"
    APPROVED_EXPERIMENTAL = "approved_for_experimentation"
    APPROVED_PRODUCTION = "approved_for_production"
    REJECTED = "rejected"


class PaperRecord(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    publisher: str
    doi: str | None = None
    source_url: str | None = None
    peer_review_status: str  # peer_reviewed | government_technical | preprint | unknown
    hazard: str
    geography: str
    asset_type: str
    intensity_measure: str
    dependent_variable: str
    model_type: str
    calibration_range: str | None = None
    validation_method: str | None = None
    limitations: list[str]
    prohibited_extrapolations: str
    license_note: str
    extraction_performed: bool
    extraction_confidence: str  # none | low | medium | high
    human_review_status: ReviewStatus
    verification_note: str


class PaperSummary(BaseModel):
    paper_id: str
    title: str
    publisher: str
    year: int | None
    hazard: str
    asset_type: str
    relevance: float
    peer_review_status: str
    human_review_status: ReviewStatus


class ResearchQuery(BaseModel):
    query: str
    hazard: str | None = None
    asset_type: str | None = None


class SourceStatus(BaseModel):
    source: str
    status: str  # live | demo_index | unavailable
    note: str


class ResearchSearchResponse(BaseModel):
    query: str
    reformulated_terms: list[str]
    results: list[PaperSummary]
    source_status: list[SourceStatus]
    notice: str


class ExtractionRequestResult(BaseModel):
    paper_id: str
    accepted: bool
    new_status: ReviewStatus
    workflow: list[str]
    message: str
