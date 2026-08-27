from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
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


_ALL_GDACS_HAZARDS = ("EQ", "TC", "FL", "VO", "DR", "WF")
_ALL_GDACS_ALERTS = ("green", "orange", "red")
_HAZARD_ALIASES = {
    "EQ": "EQ",
    "EARTHQUAKE": "EQ",
    "TC": "TC",
    "CYCLONE": "TC",
    "TROPICAL_CYCLONE": "TC",
    "HURRICANE": "TC",
    "FL": "FL",
    "FLOOD": "FL",
    "VO": "VO",
    "VOLCANO": "VO",
    "VOLCANIC_ACTIVITY": "VO",
    "DR": "DR",
    "DROUGHT": "DR",
    "WF": "WF",
    "WILDFIRE": "WF",
    "FIRE": "WF",
}


def _csv_values(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace(";", ",").split(",") if item.strip()]


def _parse_hazards(value: str | None) -> tuple[str, ...]:
    raw = _csv_values(value)
    if not raw or any(item.casefold() == "all" for item in raw):
        return _ALL_GDACS_HAZARDS
    invalid = [item for item in raw if item.upper().replace(" ", "_") not in _HAZARD_ALIASES]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unsupported GDACS hazard filter: {', '.join(invalid)}")
    return tuple(dict.fromkeys(_HAZARD_ALIASES[item.upper().replace(" ", "_")] for item in raw))


def _parse_alerts(value: str | None) -> tuple[str, ...]:
    raw = [item.lower() for item in _csv_values(value)]
    if not raw or "all" in raw:
        return _ALL_GDACS_ALERTS
    invalid = [item for item in raw if item not in _ALL_GDACS_ALERTS]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unsupported GDACS alert filter: {', '.join(invalid)}")
    return tuple(dict.fromkeys(raw))


def _preset_start(window: str, end: date) -> date:
    if window == "ytd":
        return date(end.year, 1, 1)
    inclusive_days = {"today": 1, "24h": 1, "7d": 7, "30d": 30, "90d": 90}[window]
    return end - timedelta(days=inclusive_days - 1)


@router.get("/global-events", response_model=GlobalEventsResponse)
async def get_global_events(
    window: Literal["today", "24h", "7d", "30d", "90d", "ytd"] = Query(default="ytd"),
    alert: str | None = Query(default=None, description="Comma-separated GDACS levels."),
    hazard: str | None = Query(default=None, description="Comma-separated GDACS event types."),
    region: str | None = Query(default=None, max_length=120),
    q: str | None = Query(default=None, max_length=160),
    min_impact: int | None = Query(
        default=None,
        ge=1,
        le=3,
        description="Minimum GDACS alert score: 1 Green, 2 Orange, or 3 Red.",
    ),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    start_date: date | None = Query(default=None, description="Legacy alias for `from`."),
    end_date: date | None = Query(default=None, description="Legacy alias for `to`."),
    force: bool = Query(default=False, description="Bypass the short-TTL server cache for an explicit user refresh."),
    settings: Settings = Depends(settings_dep),
) -> GlobalEventsResponse:
    now = datetime.now(timezone.utc)
    if from_date and start_date and from_date != start_date:
        raise HTTPException(status_code=422, detail="`from` and `start_date` must match when both are supplied.")
    if to_date and end_date and to_date != end_date:
        raise HTTPException(status_code=422, detail="`to` and `end_date` must match when both are supplied.")
    explicit_start = from_date or start_date
    explicit_end = to_date or end_date
    end = explicit_end or now.date()
    start = explicit_start or _preset_start(window, end)
    if start > end:
        raise HTTPException(status_code=422, detail="`from` must be on or before `to`.")
    hazards = _parse_hazards(hazard)
    alerts = _parse_alerts(alert)
    response = await fetch_global_events(
        settings,
        from_date=start,
        to_date=end,
        hazards=hazards,
        alerts=alerts,
        force=force,
    )

    def matches(event) -> bool:
        haystack = " ".join(
            (
                event.event_id,
                event.event_type,
                event.name,
                event.country,
                event.source,
                event.severity_text,
                event.from_date.date().isoformat(),
                event.to_date.date().isoformat(),
            )
        ).casefold()
        score = (
            event.alert_score
            if event.alert_score is not None
            else {"green": 1, "orange": 2, "red": 3}.get(event.alert_level, 0)
        )
        return (
            (not region or region.casefold() in event.country.casefold())
            and (not q or q.casefold() in haystack)
            and (min_impact is None or score >= min_impact)
        )

    events = [event for event in response.items if matches(event)]
    levels = [event.alert_level for event in events]
    latest = max((event.modified_at for event in events), default=None)
    feed_state = (
        "feed_error" if response.status == DataStatus.UNAVAILABLE else
        "feed_degraded" if response.status == DataStatus.STALE else
        "feed_ok_no_events" if not events else "feed_ok"
    )
    local_filters: dict[str, str | int] = {}
    if region:
        local_filters["region"] = region
    if q:
        local_filters["q"] = q
    if min_impact is not None:
        local_filters["min_impact"] = min_impact
    requested_window = "custom" if explicit_start or explicit_end else window
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
        stale=response.status == DataStatus.STALE,
        result_cap=500,
        possibly_truncated="retrieval cap" in (response.note or "").lower(),
        error=response.note if response.status == DataStatus.UNAVAILABLE else None,
        feed_state=feed_state,
        requested_window=requested_window,
        effective_window=requested_window,
        window_start=start,
        window_end=end,
        auto_widened=False,
        last_successful_poll_at=response.retrieved_at if response.status != DataStatus.UNAVAILABLE else None,
        query_endpoint=response.request_url,
        query_parameters=response.request_params,
        local_filters=local_filters,
        feed_message=response.note,
        response_mode=response.response_mode,
        snapshot_retrieved_at=response.snapshot_retrieved_at,
    )


@router.get("/warm")
async def warm_global_event_cache(settings: Settings = Depends(settings_dep)) -> dict[str, object]:
    """Warm broad teaching windows without sending a burst of GDACS calls."""
    today = datetime.now(timezone.utc).date()
    windows = {
        "90d": today - timedelta(days=89),
        "ytd": date(today.year, 1, 1),
    }
    results = {}
    for label, start in windows.items():
        result = await fetch_global_events(settings, from_date=start, to_date=today, force=True)
        results[label] = {"status": result.status.value, "count": len(result.items), "mode": result.response_mode}
    return {
        "status": (
            "warmed"
            if any(item["status"] != DataStatus.UNAVAILABLE.value for item in results.values())
            else "unavailable"
        ),
        "source": "GDACS",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "windows": results,
    }


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
