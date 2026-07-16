"""USGS Water Data adapter: recent streamflow / gauge height.

Real endpoint: GET {USGS_WATER_BASE_URL}/iv/?format=json&stateCd=pa&parameterCd=00065
No API key required. On failure, falls back to the two seeded demo gauges
(Monocacy Creek, Lehigh River near Bethlehem).

Env vars: ``USGS_WATER_BASE_URL`` (default https://waterservices.usgs.gov/nwis).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.data.demo.lehigh_valley_flood import build_flood_scenario
from app.schemas.common import GeoPoint, Provenance
from app.schemas.enums import DataStatus, SourceName
from app.schemas.event import SensorObservation


def _map_series(series: dict) -> SensorObservation | None:
    try:
        site = series["sourceInfo"]
        values = series["values"][0]["value"]
        if not values:
            return None
        latest = values[-1]
        lat = float(site["geoLocation"]["geogLocation"]["latitude"])
        lon = float(site["geoLocation"]["geogLocation"]["longitude"])
        return SensorObservation(
            id=f"usgs-{site['siteCode'][0]['value']}",
            sensor_id=site["siteCode"][0]["value"],
            sensor_name=site["siteName"],
            sensor_type="river_gauge",
            geometry=GeoPoint(coordinates=(lon, lat)),
            observed_at=latest["dateTime"],
            value=float(latest["value"]),
            unit="ft",
            provenance=Provenance(
                source=SourceName.USGS_WATER,
                source_organization="U.S. Geological Survey",
                source_url=f"https://waterdata.usgs.gov/monitoring-location/{site['siteCode'][0]['value']}",
                license="Public domain (U.S. Government)",
                observed_at=latest["dateTime"],
                retrieved_at=datetime.now(timezone.utc),
                data_status=DataStatus.LIVE,
            ),
        )
    except Exception:  # noqa: BLE001
        return None


async def fetch_gauge_heights(
    settings: Settings, state: str = "pa"
) -> AdapterResponse[SensorObservation]:
    payload = await safe_get_json(
        f"{settings.usgs_water_base_url}/iv/",
        {"format": "json", "stateCd": state, "parameterCd": "00065", "siteStatus": "active"},
    )
    if payload and isinstance(payload, dict):
        series_list = payload.get("value", {}).get("timeSeries", [])
        obs = [o for o in (_map_series(s) for s in series_list) if o]
        if obs:
            return AdapterResponse(source_name="USGS_WATER", status=DataStatus.LIVE, items=obs)

    demo = build_flood_scenario(mode="live_demo")
    return AdapterResponse(
        source_name="USGS_WATER",
        status=DataStatus.DEMO,
        items=demo.sensors,
        note="Live USGS Water feed unavailable; showing seeded demo gauge readings.",
    )
