"""NASA FIRMS (fire detections) adapter.

Real usage requires a registered MAP_KEY (https://firms.modaps.eosdis.nasa.gov/api/).
Without one we do not attempt the call - we go straight to the demo state,
which for this region/date is "no active fire detections", a legitimate calm
status rather than an invented one.

Env vars: ``FIRMS_MAP_KEY``.
"""

from __future__ import annotations

from app.adapters.base import AdapterResponse
from app.core.config import Settings
from app.schemas.enums import DataStatus
from app.schemas.event import HazardEvent


async def fetch_active_fires(settings: Settings) -> AdapterResponse[HazardEvent]:
    if not settings.firms_map_key:
        return AdapterResponse(
            source_name="NASA_FIRMS",
            status=DataStatus.UNAVAILABLE,
            items=[],
            note="FIRMS_MAP_KEY not configured; no fire-detection data requested.",
        )
    # A configured deployment would call:
    #   https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{bbox}/1
    # and parse CSV rows into HazardEvent(hazard_type=WILDFIRE, ...). Left as a
    # documented extension point since we do not have a demo key to validate
    # the real response shape against.
    return AdapterResponse(
        source_name="NASA_FIRMS",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note="FIRMS live integration not yet wired up in this build.",
    )
