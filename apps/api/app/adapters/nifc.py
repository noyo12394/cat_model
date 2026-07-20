"""NIFC WFIGS current wildfire-perimeter adapter.

The National Interagency Fire Center publishes the authoritative current-year
interagency wildfire perimeters as an open ArcGIS feature service (no key
required). A perimeter is a *mapped operational boundary* of a fire - an
observed extent, not a forecast and not a modelled intensity surface. This
adapter reads those perimeters so the platform can screen exposure strictly
inside an official fire boundary. It never infers fire intensity, rate of
spread, or dollar loss from a perimeter.

Consistent with ``app.adapters.base``: every call degrades to an empty result
on any failure instead of raising, so a NIFC outage cannot break a request.

Service: https://data-nifc.opendata.arcgis.com/ (WFIGS Interagency Perimeters).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.adapters.base import safe_get_json

WFIGS_PERIMETERS_URL = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Interagency_Perimeters_Current/FeatureServer/0/query"
)
NIFC_SOURCE_URL = "https://data-nifc.opendata.arcgis.com/"

# Only the attributes we surface; keeps the response small and fast enough for
# a serverless request path.
_LIST_FIELDS = ",".join(
    [
        "attr_UniqueFireIdentifier",
        "attr_IncidentName",
        "poly_IncidentName",
        "attr_IncidentSize",
        "poly_GISAcres",
        "attr_FireDiscoveryDateTime",
        "attr_PercentContained",
        "attr_POOState",
        "attr_IncidentTypeCategory",
        "attr_ModifiedOnDateTime_dt",
        "attr_FireCause",
    ]
)

# A UniqueFireIdentifier looks like ``2026-CACDD-001234``; restrict the value
# that is interpolated into a where-clause to this alphabet so a caller cannot
# inject SQL into the ArcGIS query.
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass
class WildfirePerimeter:
    event_id: str
    name: str
    acres: float | None
    percent_contained: float | None
    discovered_at: datetime | None
    modified_at: datetime | None
    state: str | None
    cause: str | None
    center: tuple[float, float] | None


def _first(props: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = props.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_utc(value: Any) -> datetime | None:
    """ArcGIS date fields arrive as epoch milliseconds (numbers); some layers
    emit ISO strings. Accept either and never raise."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _state(value: Any) -> str | None:
    """POOState is published like ``US-CA``; keep only the two-letter state."""
    if not value:
        return None
    text = str(value)
    return text.split("-")[-1].strip() or None


def _perimeter_from_feature(feature: dict[str, Any]) -> WildfirePerimeter | None:
    props = feature.get("attributes") or feature.get("properties") or {}
    event_id = _first(props, "attr_UniqueFireIdentifier")
    name = _first(props, "attr_IncidentName", "poly_IncidentName")
    if not event_id or not name:
        return None
    centroid = feature.get("centroid") or {}
    center: tuple[float, float] | None = None
    if isinstance(centroid, dict) and centroid.get("x") is not None and centroid.get("y") is not None:
        lon, lat = _as_float(centroid.get("x")), _as_float(centroid.get("y"))
        if lon is not None and lat is not None:
            center = (lon, lat)
    return WildfirePerimeter(
        event_id=str(event_id),
        name=str(name),
        acres=_as_float(_first(props, "attr_IncidentSize", "poly_GISAcres")),
        percent_contained=_as_float(_first(props, "attr_PercentContained")),
        discovered_at=_as_utc(_first(props, "attr_FireDiscoveryDateTime")),
        modified_at=_as_utc(_first(props, "attr_ModifiedOnDateTime_dt")),
        state=_state(_first(props, "attr_POOState")),
        cause=_first(props, "attr_FireCause"),
        center=center,
    )


async def fetch_active_wildfire_perimeters(limit: int = 20) -> list[WildfirePerimeter] | None:
    """Return current wildfire perimeters ordered by size (largest first).

    Returns ``None`` when the authoritative service could not be reached, which
    the caller reports as ``unavailable`` rather than as "no active fires".
    """
    payload = await safe_get_json(
        WFIGS_PERIMETERS_URL,
        params={
            "where": "attr_IncidentTypeCategory='WF'",
            "outFields": _LIST_FIELDS,
            "orderByFields": "attr_IncidentSize DESC",
            "resultRecordCount": max(1, min(limit, 50)),
            "returnGeometry": "false",
            "returnCentroid": "true",
            "f": "json",
        },
    )
    if not isinstance(payload, dict) or "features" not in payload:
        return None
    perimeters = [_perimeter_from_feature(feature) for feature in payload.get("features", [])]
    return [perimeter for perimeter in perimeters if perimeter is not None]


async def fetch_wildfire_perimeter_geometry(event_id: str) -> list[dict[str, Any]]:
    """Return the official perimeter polygon(s) for one incident as GeoJSON.

    The geometry is the authoritative mapped boundary; it is returned verbatim
    for point-in-polygon exposure screening and is never re-shaped into an
    intensity or probability surface.
    """
    if not _SAFE_ID.match(event_id or ""):
        return []
    payload = await safe_get_json(
        WFIGS_PERIMETERS_URL,
        params={
            "where": f"attr_UniqueFireIdentifier='{event_id}'",
            "outFields": "attr_UniqueFireIdentifier,attr_IncidentName,attr_IncidentSize",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
        },
    )
    if not isinstance(payload, dict):
        return []
    return [
        feature
        for feature in payload.get("features", [])
        if isinstance(feature, dict) and feature.get("geometry")
    ]
