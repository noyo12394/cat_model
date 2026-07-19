"""USGS Water Data OGC adapter: latest gauge-height observations.

Real endpoint: ``/collections/latest-continuous/items`` with parameter 00065.
No API key is required. Provisional readings preserve their USGS approval
status as a quality flag. On failure, the response falls back to two clearly
labelled demonstration gauges for the Bethlehem scenario.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.data.demo.lehigh_valley_flood import build_flood_scenario
from app.schemas.common import GeoPoint, Provenance
from app.schemas.enums import DataStatus, SourceName
from app.schemas.event import SensorObservation


STATE_FIPS = {"pa": "42"}


def _map_feature(feature: dict) -> SensorObservation | None:
    try:
        properties = feature["properties"]
        coordinates = feature["geometry"]["coordinates"]
        location_id = str(properties["monitoring_location_id"])
        site_id = location_id.removeprefix("USGS-")
        observed_at = properties["time"]
        approval = str(properties.get("approval_status") or "unknown")
        return SensorObservation(
            id=f"usgs-{site_id}",
            sensor_id=site_id,
            sensor_name=str(properties.get("monitoring_location_name") or f"USGS gauge {site_id}"),
            sensor_type="river_gauge",
            geometry=GeoPoint(coordinates=(float(coordinates[0]), float(coordinates[1]))),
            observed_at=observed_at,
            value=float(properties["value"]),
            unit=str(properties.get("unit_of_measure") or "unknown"),
            quality_flags=[f"USGS approval status: {approval}"],
            provenance=Provenance(
                source=SourceName.USGS_WATER,
                source_organization="U.S. Geological Survey",
                source_url=f"https://waterdata.usgs.gov/monitoring-location/{site_id}/",
                license="Public domain (U.S. Government)",
                observed_at=observed_at,
                retrieved_at=datetime.now(timezone.utc),
                data_status=DataStatus.LIVE,
            ),
        )
    except Exception:  # noqa: BLE001
        return None


async def fetch_gauge_heights(
    settings: Settings, state: str = "pa"
) -> AdapterResponse[SensorObservation]:
    state_code = STATE_FIPS.get(state.lower())
    if state_code is None:
        return AdapterResponse(
            source_name="USGS_WATER",
            status=DataStatus.UNAVAILABLE,
            items=[],
            note=f"Unsupported state code '{state}'; this MVP currently configures Pennsylvania only.",
        )
    payload = await safe_get_json(
        f"{settings.usgs_water_base_url}/collections/latest-continuous/items",
        {"f": "json", "state_code": state_code, "parameter_code": "00065", "limit": 500},
    )
    if payload and isinstance(payload, dict):
        obs = [o for o in (_map_feature(item) for item in payload.get("features", [])) if o]
        if obs:
            return AdapterResponse(source_name="USGS_WATER", status=DataStatus.LIVE, items=obs)

    demo = build_flood_scenario(mode="live_demo")
    return AdapterResponse(
        source_name="USGS_WATER",
        status=DataStatus.DEMO,
        items=demo.sensors,
        note="Live USGS Water feed unavailable; showing seeded demo gauge readings.",
    )
