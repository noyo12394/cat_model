"""Research & formula-discovery API (section 12)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.research import (
    ExtractionRequestResult,
    PaperRecord,
    ResearchQuery,
    ResearchSearchResponse,
)
from app.services.research import get_paper, request_extraction, search

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/search", response_model=ResearchSearchResponse)
def research_search(body: ResearchQuery) -> ResearchSearchResponse:
    return search(body.query, body.hazard, body.asset_type)


@router.get("/papers/{paper_id}", response_model=PaperRecord)
def research_paper(paper_id: str) -> PaperRecord:
    paper = get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found in index")
    return paper


@router.post("/papers/{paper_id}/extract", response_model=ExtractionRequestResult)
def research_extract(paper_id: str) -> ExtractionRequestResult:
    """Open a human-review task. This never implements or promotes a formula."""
    result = request_extraction(paper_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Paper not found in index")
    return result
