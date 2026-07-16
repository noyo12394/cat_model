"""AirNow adapter: current AQI by area.

Real usage requires an API key (https://docs.airnowapi.org/). Without one we
fall back to a labeled demo reading consistent with the Location Capsule
example in section 8 ("Air quality is moderate").

Env vars: ``AIRNOW_API_KEY``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse
from app.core.config import Settings
from app.schemas.common import GeoPoint, Provenance
from app.schemas.enums import DataStatus, SourceName
from app.schemas.event import SensorObservation


async def fetch_current_aqi(
    settings: Settings, center: tuple[float, float]
) -> AdapterResponse[SensorObservation]:
    if not settings.airnow_api_key:
        demo = SensorObservation(
            id="airnow-demo-bethlehem",
            sensor_id="airnow-demo-bethlehem",
            sensor_name="Bethlehem area (demo)",
            sensor_type="air_quality_monitor",
            geometry=GeoPoint(coordinates=center),
            observed_at=datetime.now(timezone.utc),
            value=62,
            unit="AQI",
            provenance=Provenance(
                source=SourceName.AIRNOW,
                source_organization="AirNow (demo)",
                license="demonstration fixture",
                observed_at=datetime.now(timezone.utc),
                retrieved_at=datetime.now(timezone.utc),
                data_status=DataStatus.DEMO,
            ),
        )
        return AdapterResponse(
            source_name="AIRNOW",
            status=DataStatus.DEMO,
            items=[demo],
            note="AIRNOW_API_KEY not configured; showing a demo moderate-AQI reading.",
        )
    # A configured deployment would call AirNow's /aq/observation/latLong/current
    # endpoint and map the JSON response into SensorObservation. Left as a
    # documented extension point pending a real API key to validate against.
    return AdapterResponse(
        source_name="AIRNOW",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note="AirNow live integration not yet wired up in this build.",
    )
