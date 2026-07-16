from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import settings_dep
from app.core.config import Settings
from app.services.source_health import SourceStatus, get_source_health

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/status", response_model=list[SourceStatus])
async def source_status(settings: Settings = Depends(settings_dep)) -> list[SourceStatus]:
    return await get_source_health(settings)
