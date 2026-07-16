"""GDACS global multi-hazard event adapter.

Uses the official MHEWS GeoJSON API documented by GDACS. A feed failure returns
UNAVAILABLE and an empty list; it never substitutes synthetic global events.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent

_CACHE_TTL_SECONDS = 300
_cache: tuple[float, AdapterResponse[GlobalEvent]] | None = None


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
            event_id=f"{event_type}-{event_id}",
            event_type=event_type,
            name=props.get("name") or props.get("description") or f"GDACS {event_type} event",
            country=props.get("country") or "Location not specified",
            alert_level=str(props.get("alertlevel") or "Green").lower(),
            alert_score=float(props["alertscore"]) if props.get("alertscore") is not None else None,
            severity_text=severity.get("severitytext") or "Severity detail unavailable",
            from_date=_utc(props.get("fromdate")),
            to_date=_utc(props.get("todate") or props.get("fromdate")),
            modified_at=_utc(props.get("datemodified") or props.get("todate") or props.get("fromdate")),
            center=_center(feature.get("geometry") or {}),
            source=props.get("source") or "GDACS",
            report_url=_secure_url(urls.get("report"), report_fallback),
            geometry_url=_secure_url(urls.get("geometry"), report_fallback) if urls.get("geometry") else None,
            is_current=str(props.get("iscurrent", "true")).lower() == "true",
            data_status=DataStatus.LIVE,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        return None


async def fetch_global_events(settings: Settings, *, force: bool = False) -> AdapterResponse[GlobalEvent]:
    global _cache
    now = time.monotonic()
    if not force and _cache and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1]

    url = f"{settings.gdacs_base_url.rstrip('/')}/events/geteventlist/SEARCH"
    payload = await safe_get_json(
        url,
        params={
            "eventlist": "EQ;TC;FL;VO;DR;WF",
            "alertlevel": "green;orange;red",
            "pagesize": 100,
            "pagenumber": 1,
        },
    )
    if payload and isinstance(payload, dict) and isinstance(payload.get("features"), list):
        events = [event for event in (_map_feature(item) for item in payload["features"]) if event]
        result = AdapterResponse(
            source_name="GDACS",
            status=DataStatus.LIVE,
            items=events,
            note=f"{len(events)} current global events returned by the official GDACS API.",
        )
        _cache = (now, result)
        return result

    return AdapterResponse(
        source_name="GDACS",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note="Official GDACS global event feed is currently unavailable; no substitute events are shown.",
    )
