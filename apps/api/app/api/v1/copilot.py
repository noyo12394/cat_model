"""RiskChain AI copilot API (section 13, deliverable 10).

POST /copilot/chat interprets intent, runs approved tools, and returns a
structured, schema-validated response in which no number came from the LLM.
GET endpoints expose the approved tool registry and the frontend component
catalogue (deliverable 11).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import repo_dep, settings_dep
from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.copilot import (
    ComponentCatalogueEntry,
    CopilotRequest,
    CopilotResponse,
    ToolDescriptor,
)
from app.services.ai.catalogue import COMPONENT_CATALOGUE
from app.services.ai.orchestrator import answer
from app.services.ai.tools import list_tool_descriptors

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/chat", response_model=CopilotResponse)
def chat(
    body: CopilotRequest,
    repo: MemoryRepository = Depends(repo_dep),
    settings: Settings = Depends(settings_dep),
) -> CopilotResponse:
    return answer(body, repo, settings)


@router.get("/tools", response_model=list[ToolDescriptor])
def tools() -> list[ToolDescriptor]:
    return list_tool_descriptors()


@router.get("/component-catalogue", response_model=list[ComponentCatalogueEntry])
def component_catalogue() -> list[ComponentCatalogueEntry]:
    return COMPONENT_CATALOGUE
