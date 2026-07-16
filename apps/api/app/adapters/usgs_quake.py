"""USGS earthquake adapter: real-time GeoJSON summary feed.

Real endpoint: {USGS_QUAKE_BASE_URL}/summary/2.5_day.geojson - no API key
required. Demo fallback is an EMPTY list with a note, because "no significant
recent earthquake nearby" is itself a legitimate, calm status the product
should be able to show (see the Location Capsule example in section 8).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.common import GeoPoint, Provenance
from app.schemas.enums import CertaintyClass, DataStatus, HazardType, Severity, SourceName, Urgency
from app.schemas.event import HazardEvent


def _map_feature(feature: dict) -> HazardEvent | None:
    try:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]  # [lon, lat, depth_km]
        mag = props.get("mag") or 0.0
        severity = (
            Severity.EXTREME
            if mag >= 7
            else Severity.SEVERE
            if mag >= 6
            else Severity.ELEVATED
            if mag >= 4.5
            else Severity.WATCH
            if mag >= 2.5
            else Severity.NORMAL
        )
        observed = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc)
        return HazardEvent(
            id=f"usgs-quake-{feature['id']}",
            event_id=feature["id"],
            hazard_type=HazardType.EARTHQUAKE,
            status=CertaintyClass.OBSERVED,
            headline=props.get("title", f"Magnitude {mag} earthquake"),
            description=props.get("place", ""),
            severity=severity,
            certainty=CertaintyClass.OBSERVED,
            urgency=Urgency.PAST,
            observed_at=observed,
            updated_at=observed,
            geometry=GeoPoint(coordinates=(coords[0], coords[1])),
            measurements={"magnitude": mag, "depth_km": coords[2] if len(coords) > 2 else 0.0},
            provenance=Provenance(
                source=SourceName.USGS_QUAKE,
                source_organization="U.S. Geological Survey",
                source_url=props.get("url"),
                license="Public domain (U.S. Government)",
                observed_at=observed,
                retrieved_at=datetime.now(timezone.utc),
                data_status=DataStatus.LIVE,
            ),
        )
    except Exception:  # noqa: BLE001
        return None


async def fetch_recent_earthquakes(settings: Settings) -> AdapterResponse[HazardEvent]:
    payload = await safe_get_json(f"{settings.usgs_quake_base_url}/summary/2.5_day.geojson")
    if payload and isinstance(payload, dict) and "features" in payload:
        quakes = [q for q in (_map_feature(f) for f in payload["features"]) if q]
        return AdapterResponse(source_name="USGS_QUAKE", status=DataStatus.LIVE, items=quakes)

    return AdapterResponse(
        source_name="USGS_QUAKE",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note="Live USGS earthquake feed unavailable. No recent-earthquake status to show.",
    )
