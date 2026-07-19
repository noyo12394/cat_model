from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import settings_dep
from app.adapters.source_registry import SOURCE_REGISTRY
from app.core.config import Settings
from app.schemas.source_registry import SourceRegistryRecord
from app.services.source_health import SourceStatus, get_source_health

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/registry", response_model=list[SourceRegistryRecord])
def source_registry() -> list[SourceRegistryRecord]:
    """Return governed source metadata; no source is implied to be production-ready."""
    return [SourceRegistryRecord.model_validate(item.__dict__) for item in SOURCE_REGISTRY]


@router.get("/status", response_model=list[SourceStatus])
async def source_status(settings: Settings = Depends(settings_dep)) -> list[SourceStatus]:
    return await get_source_health(settings)
