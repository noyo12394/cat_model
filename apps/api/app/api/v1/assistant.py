from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import repo_dep, settings_dep
from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.assistant import AssistantAnswer, AssistantQuery
from app.services.assistant import answer_question

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantAnswer)
def query(
    body: AssistantQuery,
    repo: MemoryRepository = Depends(repo_dep),
    settings: Settings = Depends(settings_dep),
) -> AssistantAnswer:
    return answer_question(repo, settings, body.question)
