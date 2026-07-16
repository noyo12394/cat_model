from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.schemas.event import Alert, HazardEvent, SensorObservation

router = APIRouter(prefix="/live", tags=["live"])


class LiveEventsResponse(BaseModel):
    events: list[HazardEvent]
    alerts: list[Alert]
    sensors: list[SensorObservation]
    generated_at: datetime


class RegionSummary(BaseModel):
    region_label: str
    active_incident_count: int
    active_alert_count: int
    rising_gauge_count: int
    headline: str
    generated_at: datetime
    is_demo: bool = True


@router.get("/events", response_model=LiveEventsResponse)
def get_live_events(repo: MemoryRepository = Depends(repo_dep)) -> LiveEventsResponse:
    return LiveEventsResponse(
        events=repo.list_events(mode="live"),
        alerts=repo.list_alerts(mode="live"),
        sensors=repo.list_sensors(mode="live"),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/summary", response_model=RegionSummary)
def get_live_summary(repo: MemoryRepository = Depends(repo_dep)) -> RegionSummary:
    incidents = repo.list_incidents(mode="live")
    alerts = repo.list_alerts(mode="live")
    sensors = repo.list_sensors(mode="live")
    rising = [s for s in sensors if (s.trend_per_hour or 0) > 0.3]
    headline = (
        incidents[0].one_line_summary
        if incidents
        else "No active incidents are being tracked right now."
    )
    return RegionSummary(
        region_label="Lehigh Valley, PA (demo region)",
        active_incident_count=len(incidents),
        active_alert_count=len(alerts),
        rising_gauge_count=len(rising),
        headline=headline,
        generated_at=datetime.now(timezone.utc),
    )
