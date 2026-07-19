from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.adapters.nominatim import geocode_address
from app.api.deps import repo_dep, settings_dep
from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.place import LocationCapsule
from app.services.location_capsule import build_location_capsule

router = APIRouter(prefix="/places", tags=["places"])


class PlaceSearchResult(BaseModel):
    place_id: str
    name: str
    center: tuple[float, float]
    provider: str = "RiskChain place directory"
    data_status: str = "demo"


class PlaceSearchResponse(BaseModel):
    query: str
    results: list[PlaceSearchResult]


@router.get("/search", response_model=PlaceSearchResponse)
async def search_places(
    q: str = Query(..., min_length=1, max_length=200),
    repo: MemoryRepository = Depends(repo_dep),
    settings: Settings = Depends(settings_dep),
) -> PlaceSearchResponse:
    matches = repo.search_places(q)
    if matches:
        results = [
            PlaceSearchResult(place_id=m["place_id"], name=m["name"], center=m["center"])
            for m in matches
        ]
    else:
        geocoded = await geocode_address(q, settings)
        results = [
            PlaceSearchResult(
                place_id=m.place_id,
                name=m.name,
                center=m.center,
                provider=m.provider,
                data_status=m.data_status,
            )
            for m in geocoded
        ]
    return PlaceSearchResponse(
        query=q,
        results=results,
    )


@router.get("/{place_id}", response_model=PlaceSearchResult)
def get_place(place_id: str, repo: MemoryRepository = Depends(repo_dep)) -> PlaceSearchResult:
    place = repo.get_place(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return PlaceSearchResult(place_id=place["place_id"], name=place["name"], center=place["center"])


@router.get("/{place_id}/capsule", response_model=LocationCapsule)
def get_place_capsule(place_id: str, repo: MemoryRepository = Depends(repo_dep)) -> LocationCapsule:
    capsule = build_location_capsule(repo, place_id)
    if not capsule:
        raise HTTPException(status_code=404, detail="Place not found")
    return capsule


@router.get("/{place_id}/conditions", response_model=LocationCapsule)
def get_place_conditions(place_id: str, repo: MemoryRepository = Depends(repo_dep)) -> LocationCapsule:
    """Alias of /capsule matching the section 36 suggested endpoint name."""
    return get_place_capsule(place_id, repo)


@router.get("/{place_id}/history")
def get_place_history(place_id: str, repo: MemoryRepository = Depends(repo_dep)) -> dict:
    place = repo.get_place(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return {
        "place_id": place_id,
        "note": (
            "Historical time series for this place is not populated in this build beyond the "
            "seeded replay incident. Use /api/v1/incidents?mode=replay for the full replay."
        ),
    }
