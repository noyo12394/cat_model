from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.adapters.gdacs import fetch_global_events
from app.adapters.nhc import fetch_nhc_forecast_tracks
from app.adapters.x_community import fetch_x_community_posts
from app.api.deps import repo_dep, settings_dep
from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.compound import MultiHazardOverview
from app.schemas.community_signals import CommunitySignalsResponse
from app.schemas.enums import DataStatus
from app.schemas.event import Alert, HazardEvent, SensorObservation
from app.schemas.global_event import GlobalEventCounts, GlobalEventsResponse
from app.schemas.global_outlook import GlobalOutlookResponse
from app.schemas.future_outlook import FutureOutlookResponse
from app.schemas.weather_model_outlook import ModelWeatherOutlookResponse
from app.services.compound_intelligence import build_compound_events
from app.services.community_signals import build_community_signals, unavailable_community_signals
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
async def get_global_events(
    window: Literal["24h", "7d", "30d", "90d", "ytd"] = Query(default="30d"),
    alert: str | None = Query(default=None, description="Comma-separated GDACS levels."),
    hazard: str | None = Query(default=None, description="Comma-separated GDACS event types."),
    region: str | None = Query(default=None, max_length=120),
    q: str | None = Query(default=None, max_length=160),
    start_date: date | None = None,
    end_date: date | None = None,
    force: bool = Query(default=False, description="Bypass the short-TTL server cache for an explicit user refresh."),
    settings: Settings = Depends(settings_dep),
) -> GlobalEventsResponse:
    now = datetime.now(timezone.utc)
    window_days = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    end = end_date or now.date()
    start = start_date or (date(now.year, 1, 1) if window == "ytd" else end - timedelta(days=window_days[window]))
    hazards = tuple(item for item in (hazard or "EQ,TC,FL,VO,DR,WF").upper().split(",") if item in {"EQ", "TC", "FL", "VO", "DR", "WF"}) or ("EQ", "TC", "FL", "VO", "DR", "WF")
    alerts = tuple(item for item in (alert or "green,orange,red").lower().split(",") if item in {"green", "orange", "red"}) or ("green", "orange", "red")
    response = await fetch_global_events(settings, from_date=start, to_date=end, hazards=hazards, alerts=alerts, force=force)

    def matches(event) -> bool:
        haystack = f"{event.event_id} {event.name} {event.country}".casefold()
        return (not region or region.casefold() in event.country.casefold()) and (not q or q.casefold() in haystack)

    events = [event for event in response.items if matches(event)]
    effective_window = window
    auto_widened = False
    if not events and not start_date and window in {"24h", "7d", "30d"}:
        next_window = {"24h": "7d", "7d": "30d", "30d": "90d"}[window]
        wider_start = end - timedelta(days=window_days[next_window])
        wider = await fetch_global_events(settings, from_date=wider_start, to_date=end, hazards=hazards, alerts=alerts, force=force)
        wider_events = [event for event in wider.items if matches(event)]
        if wider_events:
            response, events, start, effective_window, auto_widened = wider, wider_events, wider_start, next_window, True
    levels = [event.alert_level for event in events]
    latest = max((event.modified_at for event in events), default=None)
    age_seconds = (now - latest).total_seconds() if latest else None
    feed_state = (
        "feed_error" if response.status == DataStatus.UNAVAILABLE else
        "feed_degraded" if response.status == DataStatus.STALE else
        "feed_ok_no_events" if not events else "feed_ok"
    )
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
        result_cap=500,
        possibly_truncated=len(events) >= 500,
        error=response.note if response.status == DataStatus.UNAVAILABLE else None,
        feed_state=feed_state,
        requested_window=window,
        effective_window=effective_window,
        window_start=start,
        window_end=end,
        auto_widened=auto_widened,
        last_successful_poll_at=response.retrieved_at if response.status != DataStatus.UNAVAILABLE else None,
        query_endpoint=response.request_url,
        query_parameters=response.request_params,
    )


@router.get("/warm")
async def warm_global_event_cache(settings: Settings = Depends(settings_dep)) -> dict[str, str]:
    """Warm every teaching-window variant so a workshop does not start cold."""
    today = datetime.now(timezone.utc).date()
    starts = [today - timedelta(days=days) for days in (1, 7, 30, settings.live_window_days)] + [date(today.year, 1, 1)]
    await asyncio.gather(*(fetch_global_events(settings, from_date=start, to_date=today) for start in starts))
    return {"status": "warmed", "source": "GDACS", "retrieved_at": datetime.now(timezone.utc).isoformat()}


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


@router.get("/community-signals/{event_id}", response_model=CommunitySignalsResponse)
async def get_community_signals(
    event_id: str,
    settings: Settings = Depends(settings_dep),
) -> CommunitySignalsResponse:
    """Return source-linked, unverified community language for one GDACS event.

    Community posts are never joined into official alert levels, forecasts, or
    EarthPulse watch scores. An unavailable source remains visibly unavailable.
    """
    feed = await fetch_global_events(settings)
    event = next((item for item in feed.items if item.event_id == event_id), None)
    if event is None:
        return unavailable_community_signals(
            event_id,
            "The selected official event is no longer available in the current GDACS feed, so no community search was run.",
        )
    posts = await fetch_x_community_posts(event, settings)
    return build_community_signals(event, posts)


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
