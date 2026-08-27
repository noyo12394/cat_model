"""Windowed GDACS adapter with resilient cache and cited snapshot fallbacks.

GDACS is an operational awareness source, not an emergency warning service.
The adapter therefore keeps the source status explicit: live responses stay
``LIVE``; incomplete, cached, or checked-in responses are always ``STALE``;
and a request with no usable fallback is ``UNAVAILABLE``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent

_PAGE_SIZE = 100
_MAX_PAGES = 5
_SUPPORTED_HAZARDS = ("EQ", "TC", "FL", "VO", "DR", "WF")
_SUPPORTED_ALERTS = ("green", "orange", "red")
_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "live" / "gdacs_2026_ytd_snapshot.json"
_logger = logging.getLogger("earthpulse.adapters.gdacs")


@dataclass(frozen=True)
class _CacheEntry:
    stored_at: float
    start: date
    end: date
    hazards: frozenset[str]
    alerts: frozenset[str]
    response: AdapterResponse[GlobalEvent]


@dataclass(frozen=True)
class _Snapshot:
    retrieved_at: datetime
    start: date
    end: date
    items: tuple[GlobalEvent, ...]
    source_url: str


_cache: dict[tuple[str, ...], _CacheEntry] = {}


def _utc(value: str | None) -> datetime:
    if not value:
        raise ValueError("GDACS record did not include a timestamp")
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
        from_timestamp = props.get("fromdate")
        return GlobalEvent(
            event_id=f"{event_type}-{event_id}",
            event_type=event_type,
            name=props.get("name") or props.get("description") or f"GDACS {event_type} event",
            country=props.get("country") or "Location not specified",
            alert_level=str(props.get("alertlevel") or "Green").lower(),
            alert_score=float(props["alertscore"]) if props.get("alertscore") is not None else None,
            severity_text=severity.get("severitytext") or "Severity detail unavailable",
            from_date=_utc(from_timestamp),
            to_date=_utc(props.get("todate") or from_timestamp),
            modified_at=_utc(props.get("datemodified") or props.get("todate") or from_timestamp),
            center=_center(feature.get("geometry") or {}),
            source=props.get("source") or "GDACS",
            report_url=_secure_url(urls.get("report"), report_fallback),
            geometry_url=_secure_url(urls.get("geometry"), report_fallback) if urls.get("geometry") else None,
            is_current=str(props.get("iscurrent", "true")).lower() == "true",
            data_status=DataStatus.LIVE,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def request_params(
    from_date: date,
    to_date: date,
    hazards: tuple[str, ...],
    alerts: tuple[str, ...],
    page: int,
) -> dict[str, str | int]:
    """Return the documented public GDACS search parameters verbatim."""
    return {
        "eventlist": ";".join(hazards),
        "alertlevel": ";".join(alerts),
        "fromdate": from_date.isoformat(),
        "todate": to_date.isoformat(),
        "pagesize": _PAGE_SIZE,
        "pagenumber": page,
    }


def _normalize_hazards(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(item.upper() for item in values if item.upper() in _SUPPORTED_HAZARDS))
    return normalized or _SUPPORTED_HAZARDS


def _normalize_alerts(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(item.lower() for item in values if item.lower() in _SUPPORTED_ALERTS))
    return normalized or _SUPPORTED_ALERTS


def _overlaps(event: GlobalEvent, start: date, end: date) -> bool:
    return event.from_date.date() <= end and event.to_date.date() >= start


def _filter_events(
    events: list[GlobalEvent] | tuple[GlobalEvent, ...],
    *,
    start: date,
    end: date,
    hazards: tuple[str, ...],
    alerts: tuple[str, ...],
) -> list[GlobalEvent]:
    hazard_set = set(hazards)
    alert_set = set(alerts)
    return [
        event
        for event in events
        if event.event_type in hazard_set and event.alert_level in alert_set and _overlaps(event, start, end)
    ]


def _deduplicate(events: list[GlobalEvent]) -> list[GlobalEvent]:
    return sorted(
        {event.event_id: event for event in events}.values(),
        key=lambda event: (event.from_date, event.modified_at, event.event_id),
        reverse=True,
    )


def _cache_key(start: date, end: date, hazards: tuple[str, ...], alerts: tuple[str, ...]) -> tuple[str, ...]:
    return (start.isoformat(), end.isoformat(), *hazards, "|", *alerts)


@lru_cache(maxsize=1)
def _load_snapshot() -> _Snapshot | None:
    """Load the immutable, source-cited cold-start snapshot bundled with the API."""
    try:
        payload = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        coverage = payload["coverage"]
        mapped = [event for feature in payload["features"] if (event := _map_feature(feature))]
        items = tuple(event.model_copy(update={"data_status": DataStatus.STALE}) for event in mapped)
        return _Snapshot(
            retrieved_at=_utc(payload["retrieved_at"]),
            start=date.fromisoformat(coverage["from"]),
            end=date.fromisoformat(coverage["to"]),
            items=items,
            source_url=payload["source"]["request_url"],
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _logger.warning("GDACS checked-in snapshot could not be read: %s", exc)
        return None


def _fallback_events(
    *,
    start: date,
    end: date,
    hazards: tuple[str, ...],
    alerts: tuple[str, ...],
) -> tuple[list[GlobalEvent], datetime | None, list[str], datetime | None]:
    """Collect compatible in-memory records plus the immutable cold snapshot.

    A cache entry does not need to match the exact filtered query. Any
    overlapping entry can contribute known records; the returned response is
    labelled stale and the note states that its coverage can be partial.
    """
    events: list[GlobalEvent] = []
    retrieved: list[datetime] = []
    modes: list[str] = []
    requested_hazards = set(hazards)
    requested_alerts = set(alerts)

    compatible_entries = [
        entry
        for entry in _cache.values()
        if entry.start <= end
        and entry.end >= start
        and entry.hazards.intersection(requested_hazards)
        and entry.alerts.intersection(requested_alerts)
    ]
    if compatible_entries:
        modes.append("memory cache")
        retrieved.extend(entry.response.retrieved_at for entry in compatible_entries)
        for entry in compatible_entries:
            events.extend(entry.response.items)

    snapshot = _load_snapshot()
    snapshot_retrieved_at: datetime | None = None
    if snapshot and snapshot.start <= end and snapshot.end >= start:
        modes.append("checked-in GDACS snapshot")
        retrieved.append(snapshot.retrieved_at)
        snapshot_retrieved_at = snapshot.retrieved_at
        events.extend(snapshot.items)

    filtered = _filter_events(events, start=start, end=end, hazards=hazards, alerts=alerts)
    stale_events = [event.model_copy(update={"data_status": DataStatus.STALE}) for event in filtered]
    return _deduplicate(stale_events), max(retrieved, default=None), modes, snapshot_retrieved_at


async def _fetch_pages(
    url: str,
    *,
    start: date,
    end: date,
    hazards: tuple[str, ...],
    alerts: tuple[str, ...],
) -> tuple[list[dict], int | None]:
    """Fetch source pages sequentially to avoid GDACS throttling bursts.

    A single retry is used for the first page because without it no live result
    is usable. Pagination stops as soon as GDACS returns fewer than ``pagesize``
    records, matching the official API guidance.
    """
    payloads: list[dict] = []
    failed_page: int | None = None
    for page in range(1, _MAX_PAGES + 1):
        params = request_params(start, end, hazards, alerts, page)
        payload = await safe_get_json(url, params=params)
        valid = isinstance(payload, dict) and isinstance(payload.get("features"), list)
        if not valid and page == 1:
            await asyncio.sleep(0)
            payload = await safe_get_json(url, params=params)
            valid = isinstance(payload, dict) and isinstance(payload.get("features"), list)
        if not valid:
            failed_page = page
            break
        payloads.append(payload)
        if len(payload["features"]) < _PAGE_SIZE:
            break
    return payloads, failed_page


async def fetch_global_events(
    settings: Settings,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    hazards: tuple[str, ...] = _SUPPORTED_HAZARDS,
    alerts: tuple[str, ...] = _SUPPORTED_ALERTS,
    force: bool = False,
) -> AdapterResponse[GlobalEvent]:
    end = to_date or datetime.now(timezone.utc).date()
    start = from_date or end - timedelta(days=max(settings.live_window_days - 1, 0))
    if start > end:
        raise ValueError("from_date must be on or before to_date")
    hazards = _normalize_hazards(hazards)
    alerts = _normalize_alerts(alerts)
    cache_key = _cache_key(start, end, hazards, alerts)
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if not force and cached and now - cached.stored_at < settings.gdacs_cache_ttl_seconds:
        return replace(cached.response, response_mode="memory_cache")

    url = f"{settings.gdacs_base_url.rstrip('/')}/events/geteventlist/SEARCH"
    if not force:
        fallback, retrieved_at, modes, snapshot_retrieved_at = _fallback_events(
            start=start,
            end=end,
            hazards=hazards,
            alerts=alerts,
        )
        if modes and retrieved_at:
            return AdapterResponse(
                source_name="GDACS",
                status=DataStatus.STALE,
                items=fallback,
                retrieved_at=retrieved_at,
                note=(
                    "Serving source-labelled cached records immediately from "
                    f"{' and '.join(modes)} while the scheduled feed warmer refreshes GDACS. "
                    "Coverage may be partial for this exact query."
                ),
                source_url="https://www.gdacs.org/",
                request_url=url,
                request_params=request_params(start, end, hazards, alerts, 1),
                response_mode="checked_in_snapshot" if snapshot_retrieved_at else "memory_cache",
                snapshot_retrieved_at=snapshot_retrieved_at,
            )

    payloads, failed_page = await _fetch_pages(
        url,
        start=start,
        end=end,
        hazards=hazards,
        alerts=alerts,
    )
    if payloads:
        mapped = [
            event
            for payload in payloads
            for feature in payload["features"]
            if (event := _map_feature(feature))
        ]
        events = _deduplicate(
            _filter_events(mapped, start=start, end=end, hazards=hazards, alerts=alerts)
        )
        partial = failed_page is not None
        possible_more = len(payloads) == _MAX_PAGES and len(payloads[-1]["features"]) >= _PAGE_SIZE
        result = AdapterResponse(
            source_name="GDACS",
            status=DataStatus.STALE if partial else DataStatus.LIVE,
            items=(
                [event.model_copy(update={"data_status": DataStatus.STALE}) for event in events]
                if partial
                else events
            ),
            note=(
                f"{len(events)} official records returned from {len(payloads)} GDACS page(s)."
                + (f" GDACS page {failed_page} could not be read; this is a partial response." if partial else "")
                + (" The 500-record retrieval cap was reached; older records may exist." if possible_more else "")
            ),
            source_url="https://www.gdacs.org/",
            request_url=url,
            request_params=request_params(start, end, hazards, alerts, 1),
            response_mode="partial_upstream" if partial else "upstream",
        )
        _cache[cache_key] = _CacheEntry(
            stored_at=now,
            start=start,
            end=end,
            hazards=frozenset(hazards),
            alerts=frozenset(alerts),
            response=result,
        )
        return result

    fallback, retrieved_at, modes, snapshot_retrieved_at = _fallback_events(
        start=start,
        end=end,
        hazards=hazards,
        alerts=alerts,
    )
    if modes and retrieved_at:
        return AdapterResponse(
            source_name="GDACS",
            status=DataStatus.STALE,
            items=fallback,
            retrieved_at=retrieved_at,
            note=(
                "GDACS request failed; serving source-labelled stale records from "
                f"{' and '.join(modes)}. Coverage may be partial for this exact query."
            ),
            source_url="https://www.gdacs.org/",
            request_url=url,
            request_params=request_params(start, end, hazards, alerts, 1),
            response_mode="checked_in_snapshot" if snapshot_retrieved_at else "memory_cache",
            snapshot_retrieved_at=snapshot_retrieved_at,
        )

    return AdapterResponse(
        source_name="GDACS",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note=(
            "Official GDACS global event feed is unavailable and no cached snapshot covers "
            f"{start.isoformat()} through {end.isoformat()}."
        ),
        source_url="https://www.gdacs.org/",
        request_url=url,
        request_params=request_params(start, end, hazards, alerts, 1),
        response_mode="none",
    )
