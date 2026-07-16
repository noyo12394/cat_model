"""National Weather Service adapter: active watches/warnings/advisories.

Real endpoint: GET {NWS_BASE_URL}/alerts/active?area={state} - no API key
required, but a descriptive User-Agent is expected by NWS. On any failure we
fall back to the seeded Bethlehem demo alert so the UI always has something
coherent to render, clearly labeled as demo.

Env vars: ``NWS_BASE_URL`` (default https://api.weather.gov).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.data.demo.lehigh_valley_flood import build_flood_scenario
from app.schemas.common import GeoPolygon, Provenance
from app.schemas.enums import CertaintyClass, DataStatus, HazardType, Severity, SourceName, Urgency
from app.schemas.event import Alert

_NWS_SEVERITY_MAP = {
    "Extreme": Severity.EXTREME,
    "Severe": Severity.SEVERE,
    "Moderate": Severity.ELEVATED,
    "Minor": Severity.WATCH,
    "Unknown": Severity.UNKNOWN,
}


def _map_alert(feature: dict) -> Alert | None:
    try:
        props = feature["properties"]
        geometry = feature.get("geometry")
        if geometry and geometry.get("type") == "Polygon":
            geom = GeoPolygon(coordinates=geometry["coordinates"])
        else:
            # Many NWS alerts carry no inline geometry (UGC-zone based); a real
            # implementation resolves UGC codes to shapes via NWS zone lookups.
            geom = GeoPolygon(coordinates=[[(0, 0), (0, 0), (0, 0), (0, 0)]])
        return Alert(
            id=f"nws-{props['id']}",
            alert_id=props["id"],
            source_event_id=props.get("id"),
            hazard_type=HazardType.SEVERE_WEATHER,
            headline=props.get("headline", props.get("event", "Weather alert")),
            description=props.get("description", ""),
            severity=_NWS_SEVERITY_MAP.get(props.get("severity", "Unknown"), Severity.UNKNOWN),
            certainty=CertaintyClass.OFFICIAL_ALERT,
            urgency=Urgency.IMMEDIATE if props.get("urgency") == "Immediate" else Urgency.EXPECTED,
            effective_at=props.get("effective") or datetime.now(timezone.utc).isoformat(),
            expires_at=props.get("expires"),
            geometry=geom,
            area_description=props.get("areaDesc"),
            provenance=Provenance(
                source=SourceName.NWS,
                source_organization="National Weather Service",
                source_url=props.get("@id"),
                license="Public domain (U.S. Government)",
                observed_at=props.get("effective"),
                updated_at=props.get("sent"),
                retrieved_at=datetime.now(timezone.utc),
                data_status=DataStatus.LIVE,
            ),
        )
    except Exception:  # noqa: BLE001
        return None


async def fetch_active_alerts(settings: Settings, state: str = "PA") -> AdapterResponse[Alert]:
    payload = await safe_get_json(f"{settings.nws_base_url}/alerts/active", {"area": state})
    if payload and isinstance(payload, dict) and payload.get("features"):
        alerts = [a for a in (_map_alert(f) for f in payload["features"]) if a]
        if alerts:
            return AdapterResponse(source_name="NWS", status=DataStatus.LIVE, items=alerts)

    demo = build_flood_scenario(mode="live_demo")
    return AdapterResponse(
        source_name="NWS",
        status=DataStatus.DEMO,
        items=demo.alerts,
        note="Live NWS feed unavailable or empty for this area; showing seeded demo alert.",
    )
