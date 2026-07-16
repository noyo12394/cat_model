from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.adapters.gdacs import fetch_global_events
from app.adapters.nhc import fetch_nhc_forecast_tracks
from app.api.deps import repo_dep, settings_dep
from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.compound import MultiHazardOverview
from app.schemas.enums import DataStatus
from app.schemas.event import Alert, HazardEvent, SensorObservation
from app.schemas.global_event import GlobalEventCounts, GlobalEventsResponse
from app.schemas.global_outlook import GlobalOutlookResponse
from app.schemas.future_outlook import FutureOutlookResponse
from app.schemas.weather_model_outlook import ModelWeatherOutlookResponse
from app.services.compound_intelligence import build_compound_events
from app.services.global_outlook import horizon_label, priority_for
from app.services.future_outlook import build_future_outlook
from app.services.weather_model_outlook import build_model_weather_outlook
from app.services.source_health import get_source_health

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


@router.get("/global-events", response_model=GlobalEventsResponse)
async def get_global_events(settings: Settings = Depends(settings_dep)) -> GlobalEventsResponse:
    response = await fetch_global_events(settings)
    events = response.items
    levels = [event.alert_level for event in events]
    latest = max((event.modified_at for event in events), default=None)
    age_seconds = (datetime.now(timezone.utc) - latest).total_seconds() if latest else None
    return GlobalEventsResponse(
        events=events,
        counts=GlobalEventCounts(
            total=len(events),
            red=levels.count("red"),
            orange=levels.count("orange"),
            green=levels.count("green"),
        ),
        fetched_at=response.retrieved_at,
        source_updated_at=latest,
        data_status=response.status,
        stale=response.status == DataStatus.STALE or (age_seconds is not None and age_seconds > 86400),
        error=response.note if response.status == DataStatus.UNAVAILABLE else None,
    )


@router.get("/global-outlook", response_model=GlobalOutlookResponse)
async def get_global_outlook(
    horizon_minutes: int = 15,
    settings: Settings = Depends(settings_dep),
) -> GlobalOutlookResponse:
    """Return a transparent short-horizon verification queue for live GDACS events."""
    horizon_minutes = max(0, min(horizon_minutes, 1440))
    response = await fetch_global_events(settings)
    now = datetime.now(timezone.utc)
    if response.status == DataStatus.UNAVAILABLE:
        return GlobalOutlookResponse(
            horizon_minutes=horizon_minutes,
            horizon_label=horizon_label(horizon_minutes),
            generated_at=now,
            data_status=response.status,
            error=response.note,
        )
    items = sorted(
        (priority_for(event, horizon_minutes, now=now) for event in response.items),
        key=lambda item: (-item.priority_score, item.name),
    )
    return GlobalOutlookResponse(
        horizon_minutes=horizon_minutes,
        horizon_label=horizon_label(horizon_minutes),
        generated_at=now,
        data_status=response.status,
        source_updated_at=max((event.modified_at for event in response.items), default=None),
        items=items,
    )


@router.get("/future-outlook", response_model=FutureOutlookResponse)
async def get_future_outlook(target_at: datetime) -> FutureOutlookResponse:
    """Check one future date against published, source-bounded forecast tracks.

    A date is not treated as a license to predict new disasters. At present the
    endpoint exposes official NHC named-storm tracks only; unsupported hazards
    and horizons return an explicit unavailable result.
    """
    tracks = await fetch_nhc_forecast_tracks()
    return build_future_outlook(target_at, tracks)


@router.get("/model-weather-outlook", response_model=ModelWeatherOutlookResponse)
async def get_model_weather_outlook(
    target_at: datetime,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    location_name: str = Query(default="Selected location", min_length=1, max_length=120),
) -> ModelWeatherOutlookResponse:
    """Return published model weather drivers for one explicit map location.

    This endpoint is intentionally point-scoped: it does not turn a selected
    future date into a claim that a new global disaster will happen.
    """
    return await build_model_weather_outlook(target_at, latitude, longitude, location_name)


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


@router.get("/multi-hazard", response_model=MultiHazardOverview)
async def get_multi_hazard_overview(
    repo: MemoryRepository = Depends(repo_dep),
    settings: Settings = Depends(settings_dep),
) -> MultiHazardOverview:
    source_status = await get_source_health(settings)
    return MultiHazardOverview(
        generated_at=datetime.now(timezone.utc),
        live_feed_count=sum(item.status == DataStatus.LIVE for item in source_status),
        demo_feed_count=sum(item.status == DataStatus.DEMO for item in source_status),
        unavailable_feed_count=sum(item.status == DataStatus.UNAVAILABLE for item in source_status),
        compound_events=build_compound_events(repo),
        research_notice=(
            "Research preview: evidence agreement, possible-futures branching, and verification priorities "
            "are decision-support prototypes, not operational emergency products."
        ),
    )
