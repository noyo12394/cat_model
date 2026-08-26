"""Windowed GDACS event adapter with short-TTL and stale-on-error caching."""

from __future__ import annotations

import asyncio
import time
from datetime import date, datetime, timedelta, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent

_PAGE_SIZE = 100
_MAX_PAGES = 5
_cache: dict[tuple[str, ...], tuple[float, AdapterResponse[GlobalEvent]]] = {}


def _utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _secure_url(value: str | None, fallback: str) -> str:
    return (value or fallback).replace("http://", "https://", 1)


def _center(geometry: dict) -> tuple[float, float]:
    coordinates = geometry.get("coordinates", [0.0, 0.0])
    while coordinates and isinstance(coordinates[0], list):
        coordinates = coordinates[0]
    return float(coordinates[0]), float(coordinates[1])


def _map_feature(feature: dict) -> GlobalEvent | None:
    try:
        props = feature["properties"]
        event_type = str(props["eventtype"]).upper()
        event_id = str(props["eventid"])
        urls = props.get("url") or {}
        severity = props.get("severitydata") or {}
        report_fallback = f"https://www.gdacs.org/report.aspx?eventtype={event_type}&eventid={event_id}"
        return GlobalEvent(
            event_id=f"{event_type}-{event_id}", event_type=event_type,
            name=props.get("name") or props.get("description") or f"GDACS {event_type} event",
            country=props.get("country") or "Location not specified",
            alert_level=str(props.get("alertlevel") or "Green").lower(),
            alert_score=float(props["alertscore"]) if props.get("alertscore") is not None else None,
            severity_text=severity.get("severitytext") or "Severity detail unavailable",
            from_date=_utc(props.get("fromdate")),
            to_date=_utc(props.get("todate") or props.get("fromdate")),
            modified_at=_utc(props.get("datemodified") or props.get("todate") or props.get("fromdate")),
            center=_center(feature.get("geometry") or {}), source=props.get("source") or "GDACS",
            report_url=_secure_url(urls.get("report"), report_fallback),
            geometry_url=_secure_url(urls.get("geometry"), report_fallback) if urls.get("geometry") else None,
            is_current=str(props.get("iscurrent", "true")).lower() == "true", data_status=DataStatus.LIVE,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def request_params(from_date: date, to_date: date, hazards: tuple[str, ...], alerts: tuple[str, ...], page: int) -> dict[str, str | int]:
    """Return the exact public GDACS parameters shown by the teaching UI."""
    return {
        "eventlist": ";".join(hazards), "alertlevel": ";".join(alerts),
        "fromDate": from_date.isoformat(), "toDate": to_date.isoformat(),
        "pagesize": _PAGE_SIZE, "pagenumber": page,
    }


async def fetch_global_events(
    settings: Settings, *, from_date: date | None = None, to_date: date | None = None,
    hazards: tuple[str, ...] = ("EQ", "TC", "FL", "VO", "DR", "WF"),
    alerts: tuple[str, ...] = ("green", "orange", "red"), force: bool = False,
) -> AdapterResponse[GlobalEvent]:
    end = to_date or datetime.now(timezone.utc).date()
    start = from_date or end - timedelta(days=settings.live_window_days)
    hazards = tuple(dict.fromkeys(item.upper() for item in hazards))
    alerts = tuple(dict.fromkeys(item.lower() for item in alerts))
    cache_key = (start.isoformat(), end.isoformat(), *hazards, "|", *alerts)
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if not force and cached and now - cached[0] < settings.gdacs_cache_ttl_seconds:
        return cached[1]

    url = f"{settings.gdacs_base_url.rstrip('/')}/events/geteventlist/SEARCH"
    payloads = await asyncio.gather(*(safe_get_json(url, params=request_params(start, end, hazards, alerts, page)) for page in range(1, _MAX_PAGES + 1)))
    valid_payloads = [payload for payload in payloads if payload is not None and isinstance(payload, dict) and isinstance(payload.get("features"), list)]
    if valid_payloads:
        mapped = (event for payload in valid_payloads for event in (_map_feature(item) for item in payload["features"]) if event)
        events = sorted({event.event_id: event for event in mapped}.values(), key=lambda event: event.modified_at, reverse=True)
        partial = len(valid_payloads) < _MAX_PAGES
        possible_more = len(events) >= _PAGE_SIZE * _MAX_PAGES
        result = AdapterResponse(
            source_name="GDACS", status=DataStatus.STALE if partial else DataStatus.LIVE, items=events,
            note=(f"{len(events)} official records returned from {len(valid_payloads)} GDACS page(s)."
                  + (" One or more result pages could not be read; this is a partial response." if partial else "")
                  + (" The 500-record retrieval cap was reached; older records may exist." if possible_more else "")),
            source_url="https://www.gdacs.org/", request_url=url,
            request_params=request_params(start, end, hazards, alerts, 1),
        )
        _cache[cache_key] = (now, result)
        return result

    if cached:
        previous = cached[1]
        return AdapterResponse(
            source_name=previous.source_name, status=DataStatus.STALE, items=previous.items,
            retrieved_at=previous.retrieved_at,
            note="GDACS request failed; serving the last cached snapshot for this exact query.",
            source_url=previous.source_url, request_url=url,
            request_params=request_params(start, end, hazards, alerts, 1),
        )

    return AdapterResponse(
        source_name="GDACS", status=DataStatus.UNAVAILABLE, items=[],
        note="Official GDACS global event feed is unavailable and no cached snapshot exists for this query.",
        source_url="https://www.gdacs.org/", request_url=url,
        request_params=request_params(start, end, hazards, alerts, 1),
    )
