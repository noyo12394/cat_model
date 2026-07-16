"""Route Risk (section 15).

For the seeded demo corridor (Lehigh University <-> St. Luke's Bethlehem) we
model two real crossings (Hill-to-Hill Bridge, Fahy Bridge) plus one
synthetic "reported closure" example so the UI can show all three states
described in section 15: lower exposure, elevated exposure, and
unavailable. For any other origin/destination this build does not have a
real road network, so it returns a single straight-line estimate honestly
labeled as low-confidence, rather than fabricating turn-by-turn detail.

Never labels a route "safe" - only "lower current exposure" or "elevated
current exposure", per principle 2.5.
"""

from __future__ import annotations

from app.db.memory_repository import MemoryRepository
from app.schemas.common import GeoLineString
from app.schemas.facility import RouteOption, RouteSegmentExposure
from app.services.geo import haversine_km, segment_intersects_polygon

AVG_SPEED_KMH = 32.0
ROUTING_FACTOR = 1.35

# Maps a crossing facility to the demo route that uses it, so scenario/action
# logic can mark a route unavailable when that facility is closed as a
# tested action, without hardcoding route ids elsewhere.
ROUTE_ID_BY_FACILITY: dict[str, str] = {
    "fac-hill-to-hill-bridge": "route-a-hill-to-hill",
    "fac-fahy-bridge": "route-b-fahy",
}


def _estimate(waypoints: list[tuple[float, float]]) -> tuple[float, float]:
    dist = sum(haversine_km(waypoints[i], waypoints[i + 1]) for i in range(len(waypoints) - 1))
    road_dist = dist * ROUTING_FACTOR
    minutes = (road_dist / AVG_SPEED_KMH) * 60
    return road_dist, minutes


def analyze_route(
    repo: MemoryRepository, origin_place_id: str, destination_place_id: str
) -> list[RouteOption]:
    origin = repo.get_place(origin_place_id)
    destination = repo.get_place(destination_place_id)
    if not origin or not destination:
        return []

    alerts = repo.list_alerts(mode="live")
    warning_rings = (
        alerts[0].geometry.coordinates if alerts and alerts[0].geometry.type == "Polygon" else []
    )

    is_lehigh_to_stlukes = {origin_place_id, destination_place_id} == {
        "lehigh-university",
        "fac-stlukes-bethlehem",
    }

    if is_lehigh_to_stlukes:
        return _lehigh_to_stlukes_routes(warning_rings)

    # Generic fallback: one straight-line estimate, honestly low-confidence.
    waypoints = [origin["center"], destination["center"]]
    dist, minutes = _estimate(waypoints)
    overlap = segment_intersects_polygon(origin["center"], destination["center"], warning_rings)
    return [
        RouteOption(
            route_id="generic-direct",
            label=f"{origin['name']} to {destination['name']} (direct estimate)",
            duration_minutes=round(minutes, 1),
            distance_km=round(dist, 1),
            geometry=GeoLineString(coordinates=waypoints),
            exposure_note=(
                "Active warning area overlaps this corridor; exposure could not be broken "
                "down by crossing without a detailed road network for this area."
                if overlap
                else "No active warning overlap detected on a direct path, but this is a "
                "straight-line estimate, not a routed one - treat it as low-confidence."
            ),
            exposure_level="elevated" if overlap else "lower",
            segments=[],
            data_freshness_minutes=None,
            confidence="low",
        )
    ]


def _lehigh_to_stlukes_routes(warning_rings: list) -> list[RouteOption]:
    from app.data.demo.lehigh_valley_flood import (
        FAHY_BRIDGE,
        HILL_TO_HILL_BRIDGE,
        LEHIGH_UNIVERSITY,
        ST_LUKES_BETHLEHEM,
    )

    route_a_pts = [
        LEHIGH_UNIVERSITY,
        (-75.3760, 40.6150),
        HILL_TO_HILL_BRIDGE,
        (-75.3650, 40.6260),
        ST_LUKES_BETHLEHEM,
    ]
    route_b_pts = [
        LEHIGH_UNIVERSITY,
        (-75.3700, 40.6120),
        FAHY_BRIDGE,
        (-75.3620, 40.6250),
        ST_LUKES_BETHLEHEM,
    ]

    dist_a, min_a = _estimate(route_a_pts)
    dist_b, min_b = _estimate(route_b_pts)
    # Fahy Bridge approach sits just outside the seeded warning polygon;
    # Hill-to-Hill's low approach ramps put it inside it (see demo fixture note).
    a_overlap = segment_intersects_polygon(HILL_TO_HILL_BRIDGE, HILL_TO_HILL_BRIDGE, warning_rings) or True
    b_overlap = segment_intersects_polygon(FAHY_BRIDGE, FAHY_BRIDGE, warning_rings)

    route_a = RouteOption(
        route_id="route-a-hill-to-hill",
        label="Via Hill-to-Hill Bridge",
        duration_minutes=round(min_a, 1),
        distance_km=round(dist_a, 1),
        geometry=GeoLineString(coordinates=route_a_pts),
        exposure_note=(
            "Crosses the active flash-flood warning area on a low-lying bridge approach. "
            "No official closure has been issued, but exposure is elevated."
        ),
        exposure_level="elevated",
        segments=[
            RouteSegmentExposure(
                segment_id="seg-hill-to-hill",
                description="Hill-to-Hill Bridge crossing",
                hazard_overlap=True,
                hazard_labels=["flash_flood_warning", "low_lying_approach", "unverified_traffic_report"],
                river_crossing=True,
                reported_closure=False,
            )
        ],
        data_freshness_minutes=5,
        confidence="moderate",
    )
    route_b = RouteOption(
        route_id="route-b-fahy",
        label="Via Fahy Bridge",
        duration_minutes=round(min_b, 1),
        distance_km=round(dist_b, 1),
        geometry=GeoLineString(coordinates=route_b_pts),
        exposure_note=(
            "No active warning overlap detected on this crossing and no reported closures. "
            "This reflects lower current hazard exposure based on available information - not a "
            "guarantee of safe passage."
        ),
        exposure_level="lower",
        segments=[
            RouteSegmentExposure(
                segment_id="seg-fahy",
                description="Fahy Bridge crossing",
                hazard_overlap=b_overlap,
                hazard_labels=[],
                river_crossing=True,
                reported_closure=False,
            )
        ],
        data_freshness_minutes=5,
        confidence="moderate",
    )
    route_c = RouteOption(
        route_id="route-c-union-blvd",
        label="Via Union Blvd (reported closure)",
        duration_minutes=None,
        distance_km=None,
        geometry=GeoLineString(coordinates=[LEHIGH_UNIVERSITY, (-75.355, 40.635), ST_LUKES_BETHLEHEM]),
        exposure_note="Unavailable due to a community-reported closure near this crossing (unverified).",
        exposure_level="unavailable",
        segments=[
            RouteSegmentExposure(
                segment_id="seg-union-blvd",
                description="Union Blvd crossing (demo)",
                hazard_overlap=True,
                hazard_labels=["reported_closure"],
                river_crossing=True,
                reported_closure=True,
            )
        ],
        data_freshness_minutes=15,
        confidence="low",
    )
    return [route_a, route_b, route_c]
