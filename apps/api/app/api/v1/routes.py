from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.schemas.facility import RouteOption
from app.services.route_risk import analyze_route

router = APIRouter(prefix="/routes", tags=["routes"])


class RouteAnalyzeRequest(BaseModel):
    origin_place_id: str
    destination_place_id: str


class RouteAnalyzeResponse(BaseModel):
    origin_place_id: str
    destination_place_id: str
    options: list[RouteOption]
    disclaimer: str = "No route is guaranteed safe. Exposure levels reflect available information only."


@router.post("/analyze", response_model=RouteAnalyzeResponse)
def analyze(
    body: RouteAnalyzeRequest, repo: MemoryRepository = Depends(repo_dep)
) -> RouteAnalyzeResponse:
    options = analyze_route(repo, body.origin_place_id, body.destination_place_id)
    return RouteAnalyzeResponse(
        origin_place_id=body.origin_place_id,
        destination_place_id=body.destination_place_id,
        options=options,
    )
