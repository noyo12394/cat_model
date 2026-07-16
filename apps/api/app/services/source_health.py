"""Source Health page (section 42): are our feeds actually working right now?"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from app.adapters import airnow, firms, nws, openfema, usgs_quake, usgs_water
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

    nws_resp = await nws.fetch_active_alerts(settings)
    usgs_resp = await usgs_water.fetch_gauge_heights(settings)
    quake_resp = await usgs_quake.fetch_recent_earthquakes(settings)
    fire_resp = await firms.fetch_active_fires(settings)
    air_resp = await airnow.fetch_current_aqi(settings, center=(-75.3705, 40.6259))
    fema_resp = await openfema.fetch_disaster_declarations(settings)

    by_key = {
        "NWS": nws_resp,
        "USGS_WATER": usgs_resp,
        "USGS_QUAKE": quake_resp,
        "NASA_FIRMS": fire_resp,
        "AIRNOW": air_resp,
        "OPENFEMA": fema_resp,
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
