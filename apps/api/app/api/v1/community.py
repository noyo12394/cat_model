from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.schemas.community_pulse import CommunityPulseResponse
from app.services.community_pulse import build_community_pulse

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/pulse", response_model=CommunityPulseResponse)
def get_community_pulse(
    incident_id: str = "developing-flood-bethlehem",
    repo: MemoryRepository = Depends(repo_dep),
) -> CommunityPulseResponse:
    """Deterministic sentiment analysis over categorized community reports.

    Social sensing, not an official indicator: every report is user-reported or
    unverified, and the concern index is a weighted count of sentiment tags -
    never a number invented by a language model.
    """
    return build_community_pulse(repo, incident_id=incident_id)
