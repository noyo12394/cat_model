"""Product roadmap API (deliverable 16)."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.roadmap import RoadmapResponse, get_roadmap

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("", response_model=RoadmapResponse)
def roadmap() -> RoadmapResponse:
    return get_roadmap()
