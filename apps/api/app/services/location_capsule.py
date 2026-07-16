"""Location Capsule builder (signature feature, section 8)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.memory_repository import MemoryRepository
from app.schemas.enums import Confidence
from app.schemas.place import CriticalConnection, LocationCapsule, NearbyCondition
from app.services.geo import haversine_km, point_in_polygon


def build_location_capsule(repo: MemoryRepository, place_id: str) -> LocationCapsule | None:
    place = repo.get_place(place_id)
    if not place:
        return None

    center = place["center"]
    incidents = repo.list_incidents(mode="live")
    alerts = repo.list_alerts(mode="live")
    all_sensors = repo.list_sensors(mode="live")
    latest_by_sensor: dict[str, object] = {}
    for obs in all_sensors:
        current = latest_by_sensor.get(obs.sensor_id)
        if current is None or obs.observed_at > current.observed_at:  # type: ignore[attr-defined]
            latest_by_sensor[obs.sensor_id] = obs
    sensors = list(latest_by_sensor.values())

    nearby: list[NearbyCondition] = []
    active_incident_ids: list[str] = []

    for alert in alerts:
        distance_km = None
        if alert.geometry.type == "Polygon":
            ring = alert.geometry.coordinates[0]
            distance_km = min(haversine_km(center, pt) for pt in ring)
        within_15mi = distance_km is not None and distance_km <= 24.1  # 15 miles
        nearby.append(
            NearbyCondition(
                label=(
                    f"{alert.headline}" + (" (within 15 miles)" if within_15mi else "")
                ),
                certainty_class="official_alert",
                detail=alert.area_description,
            )
        )

    rising = [s for s in sensors if (s.trend_per_hour or 0) > 0.3]
    if rising:
        nearby.append(
            NearbyCondition(
                label=f"{len(rising)} upstream gauge(s) rising",
                certainty_class="observed",
                detail=", ".join(s.sensor_name for s in rising),
            )
        )

    nearby.append(
        NearbyCondition(label="Air quality is moderate (demo)", certainty_class="demo")
    )
    nearby.append(
        NearbyCondition(
            label="No significant recent earthquake nearby", certainty_class="observed"
        )
    )

    is_directly_in_incident = False
    for inc in incidents:
        if haversine_km(center, inc.center) <= 40:
            active_incident_ids.append(inc.incident_id)
        if inc.geometry and inc.geometry.type == "Polygon" and point_in_polygon(center, inc.geometry.coordinates):
            is_directly_in_incident = True

    critical_connections: list[CriticalConnection] = []
    for facility, dist in repo.nearest_facilities(center, limit=5):
        critical_connections.append(
            CriticalConnection(
                facility_id=facility.facility_id,
                facility_type=facility.facility_type.value,
                name=facility.name,
                distance_km=round(dist, 1),
                travel_time_minutes=round(dist / 32.0 * 60 * 1.35, 1),
            )
        )

    # A place can be near a developing incident without being directly
    # inside its hazard area - keep those two facts distinct rather than
    # implying local impact just because something nearby is happening
    # (section 8's Lehigh University example: "no confirmed severe local
    # impact" while still surfacing a nearby flood advisory).
    return LocationCapsule(
        place_id=place_id,
        name=place["name"],
        center=center,
        current_status_headline=(
            "This location is inside an active hazard area - see details below"
            if is_directly_in_incident
            else "No confirmed severe local impact"
        ),
        nearby_conditions=nearby,
        next_24h_notes=[
            "Heavy rainfall is possible this evening (demo forecast).",
            "Some low-lying roads near the river may experience disruption.",
            "Forecast confidence is moderate.",
        ],
        forecast_confidence=Confidence.MODERATE,
        critical_connections=critical_connections,
        data_confidence=Confidence.MODERATE,
        last_updated=datetime.now(timezone.utc),
        active_incident_ids=active_incident_ids,
        is_demo=True,
    )
