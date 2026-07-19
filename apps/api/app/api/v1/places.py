from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.adapters.nominatim import geocode_address
from app.adapters.photon import suggest_places as suggest_geocoded_places
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
    zoom: float = 12.0


class PlaceSearchResponse(BaseModel):
    query: str
    results: list[PlaceSearchResult]


def _local_results(matches: list[dict]) -> list[PlaceSearchResult]:
    return [
        PlaceSearchResult(
            place_id=m["place_id"],
            name=m["name"],
            center=m["center"],
            zoom=float(m.get("zoom", 12.0)),
        )
        for m in matches
    ]


@router.get("/suggest", response_model=PlaceSearchResponse)
async def suggest_places(
    q: str = Query(..., min_length=2, max_length=120),
    repo: MemoryRepository = Depends(repo_dep),
    settings: Settings = Depends(settings_dep),
) -> PlaceSearchResponse:
    """Return debounced-combobox suggestions without calculating hazard or risk."""
    local = _local_results(repo.search_places(q, limit=4))
    external = await suggest_geocoded_places(q, settings, limit=6) if len(q.strip()) >= 3 else []
    seen = {item.name.casefold() for item in local}
    results = list(local)
    for item in external:
        if item.name.casefold() in seen:
            continue
        results.append(PlaceSearchResult(
            place_id=item.place_id,
            name=item.name,
            center=item.center,
            provider=item.provider,
            data_status=item.data_status,
            zoom=item.zoom,
        ))
        seen.add(item.name.casefold())
        if len(results) >= 6:
            break
    return PlaceSearchResponse(query=q, results=results)


@router.get("/search", response_model=PlaceSearchResponse)
async def search_places(
    q: str = Query(..., min_length=1, max_length=200),
    repo: MemoryRepository = Depends(repo_dep),
    settings: Settings = Depends(settings_dep),
) -> PlaceSearchResponse:
    matches = repo.search_places(q)
    if matches:
        results = _local_results(matches)
    else:
        geocoded = await geocode_address(q, settings)
        results = [
            PlaceSearchResult(
                place_id=m.place_id,
                name=m.name,
                center=m.center,
                provider=m.provider,
                data_status=m.data_status,
                zoom=m.zoom,
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
