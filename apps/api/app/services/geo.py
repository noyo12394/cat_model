"""Small geometry helpers. Kept dependency-light (no GEOS/GDAL requirement)
so the API runs anywhere Python runs; GeoPandas/Shapely are listed in
requirements for heavier raster/vector jobs (e.g. a future ingestion worker)
but the request-path hot code here uses plain math for speed and portability.
"""

from __future__ import annotations

import math

Point = tuple[float, float]  # (lon, lat)


def haversine_km(a: Point, b: Point) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def point_in_polygon(point: Point, polygon_rings: list[list[Point]]) -> bool:
    """Ray-casting point-in-polygon against the outer ring (ring 0)."""
    if not polygon_rings:
        return False
    x, y = point
    ring = polygon_rings[0]
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def segment_intersects_polygon(a: Point, b: Point, polygon_rings: list[list[Point]]) -> bool:
    """Cheap approximation: samples points along the segment and checks
    containment. Sufficient for demo-scale road/warning-polygon overlap
    checks; a production system would use Shapely's exact segment/polygon
    intersection."""
    steps = 12
    for i in range(steps + 1):
        f = i / steps
        p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        if point_in_polygon(p, polygon_rings):
            return True
    return False
