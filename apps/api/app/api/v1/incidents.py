from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.schemas.cascade import CascadeResult
from app.schemas.common import EvidenceTrail
from app.schemas.incident import IncidentDetail, IncidentSummary, WhatChanged
from app.schemas.inference import HistoricalAnalog, ImpactSequence
from app.services.cascade import run_cascade
from app.services.evidence import build_incident_evidence
from app.services.historical_analog import get_analogs_for_incident
from app.services.impact_nowcast import build_impact_sequence
from app.services.what_changed import compute_what_changed

router = APIRouter(prefix="/incidents", tags=["incidents"])

HAZARD_EXPOSED_DEMO_FACILITY = "fac-hill-to-hill-bridge"


def _get_incident_or_404(incident_id: str, mode: str, repo: MemoryRepository) -> IncidentDetail:
    incident = repo.get_incident(incident_id, mode=mode)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("", response_model=list[IncidentSummary])
def list_incidents(
    mode: str = Query("live", pattern="^(live|replay)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> list[IncidentSummary]:
    return [IncidentSummary(**inc.model_dump()) for inc in repo.list_incidents(mode=mode)]


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: str,
    mode: str = Query("live", pattern="^(live|replay)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> IncidentDetail:
    return _get_incident_or_404(incident_id, mode, repo)


@router.get("/{incident_id}/timeline")
def get_incident_timeline(
    incident_id: str,
    mode: str = Query("live", pattern="^(live|replay)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> dict:
    incident = _get_incident_or_404(incident_id, mode, repo)
    return {"incident_id": incident_id, "timeline": incident.timeline}


@router.get("/{incident_id}/forecast", response_model=ImpactSequence)
def get_incident_forecast(
    incident_id: str,
    mode: str = Query("live", pattern="^(live|replay)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> ImpactSequence:
    incident = _get_incident_or_404(incident_id, mode, repo)
    return build_impact_sequence(incident, repo, mode=mode)


@router.get("/{incident_id}/impacts", response_model=CascadeResult)
def get_incident_impacts(
    incident_id: str,
    mode: str = Query("live", pattern="^(live|replay)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> CascadeResult:
    """Living Cascade (section 14) rendered as this incident's impact graph."""
    _get_incident_or_404(incident_id, mode, repo)
    return run_cascade(repo, hazard_facility_ids=[HAZARD_EXPOSED_DEMO_FACILITY])


@router.get("/{incident_id}/evidence", response_model=list[EvidenceTrail])
def get_incident_evidence(
    incident_id: str,
    mode: str = Query("live", pattern="^(live|replay)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> list[EvidenceTrail]:
    incident = _get_incident_or_404(incident_id, mode, repo)
    return build_incident_evidence(incident, repo, mode=mode)


@router.get("/{incident_id}/what-changed", response_model=WhatChanged)
def get_what_changed(
    incident_id: str,
    mode: str = Query("live", pattern="^(live|replay)$"),
    compared_to: str = Query("1_hour", pattern="^(30_minutes|1_hour|6_hours|yesterday)$"),
    repo: MemoryRepository = Depends(repo_dep),
) -> WhatChanged:
    result = compute_what_changed(repo, incident_id, mode, compared_to)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.get("/{incident_id}/analogs", response_model=list[HistoricalAnalog])
def get_incident_analogs(
    incident_id: str, repo: MemoryRepository = Depends(repo_dep)
) -> list[HistoricalAnalog]:
    return get_analogs_for_incident(repo, incident_id)
