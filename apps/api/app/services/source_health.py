"""Source Health page (section 42): are our feeds actually working right now?"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from pydantic import BaseModel

from app.adapters import airnow, firms, gdacs, nws, openfema, usgs_quake, usgs_water
from app.adapters.source_registry import SOURCE_REGISTRY
from app.core.config import Settings
from app.schemas.enums import DataStatus


class SourceStatus(BaseModel):
    key: str
    display_name: str
    organization: str
    status: DataStatus
    detail: str
    checked_at: datetime


async def get_source_health(settings: Settings) -> list[SourceStatus]:
    now = datetime.now(timezone.utc)
    results: list[SourceStatus] = []

    gdacs_resp, nws_resp, usgs_resp, quake_resp, fire_resp, air_resp, fema_resp = await asyncio.gather(
        gdacs.fetch_global_events(settings),
        nws.fetch_active_alerts(settings),
        usgs_water.fetch_gauge_heights(settings),
        usgs_quake.fetch_recent_earthquakes(settings),
        firms.fetch_active_fires(settings),
        airnow.fetch_current_aqi(settings, center=(-75.3705, 40.6259)),
        openfema.fetch_disaster_declarations(settings),
    )

    by_key = {
        "GDACS": gdacs_resp,
        "NWS": nws_resp,
        "USGS_WATER": usgs_resp,
        "USGS_QUAKE": quake_resp,
        "NASA_FIRMS": fire_resp,
        "AIRNOW": air_resp,
        "OPENFEMA": fema_resp,
        "X_COMMUNITY": _x_source_status(settings),
        "NOMINATIM": _ConfiguredSource(
            DataStatus.LIVE,
            "Submit-only place search is configured; results remain provider-labelled and are not hazard observations.",
        ),
    }
    for descriptor in SOURCE_REGISTRY:
        resp = by_key.get(descriptor.key)
        if resp is None:
            results.append(
                SourceStatus(
                    key=descriptor.key,
                    display_name=descriptor.display_name,
                    organization=descriptor.organization,
                    status=DataStatus.UNAVAILABLE,
                    detail="Not checked in this build.",
                    checked_at=now,
                )
            )
            continue
        detail = resp.note or f"{len(resp.items)} item(s) returned."
        results.append(
            SourceStatus(
                key=descriptor.key,
                display_name=descriptor.display_name,
                organization=descriptor.organization,
                status=resp.status,
                detail=detail,
                checked_at=now,
            )
        )
    return results


class _ConfiguredSource:
    def __init__(self, status: DataStatus, note: str | None = None):
        self.status = status
        self.items: list[object] = []
        self.note = note


def _x_source_status(settings: Settings) -> _ConfiguredSource:
    if settings.x_bearer_token:
        return _ConfiguredSource(DataStatus.STALE, "Credential configured. Event-scoped X queries run only when an operator opens Community Signals.")
    return _ConfiguredSource(DataStatus.UNAVAILABLE, "X_BEARER_TOKEN not configured; no community posts or synthetic sentiment are shown.")
