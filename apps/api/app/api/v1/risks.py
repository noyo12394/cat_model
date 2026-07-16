"""Find Hidden Risks (section 30) - not in the section 36 endpoint list, but
called out as a defining feature, so it gets its own small router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.services.find_hidden_risks import HiddenRisk, find_hidden_risks

router = APIRouter(prefix="/risks", tags=["risks"])


@router.get("/hidden", response_model=list[HiddenRisk])
def hidden_risks(repo: MemoryRepository = Depends(repo_dep)) -> list[HiddenRisk]:
    return find_hidden_risks(repo)
