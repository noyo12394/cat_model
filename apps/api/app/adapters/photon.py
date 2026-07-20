"""Low-volume Photon place suggestions for the search combobox.

Photon is designed for search-as-you-type over OpenStreetMap data. The public
demo service permits reasonable project use but provides no availability
guarantee, so failures return an honest empty list and the explicit-submit
Nominatim search remains available as a fallback.
"""

from __future__ import annotations

import time

import httpx

from app.adapters.nominatim import GeocodedPlace
from app.core.config import Settings


_cache: dict[str, tuple[float, list[GeocodedPlace]]] = {}
_CACHE_SECONDS = 600.0


def _display_name(properties: dict) -> str:
    parts: list[str] = []
    for key in ("name", "city", "county", "state", "country"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip() and value.strip() not in parts:
            parts.append(value.strip())
    return ", ".join(parts)


async def suggest_places(
    query: str,
    settings: Settings,
    limit: int = 6,
) -> list[GeocodedPlace]:
    """Return source-labelled Photon suggestions or an empty list."""
    normalized = " ".join(query.split()).casefold()
    if len(normalized) < 3:
        return []
    now = time.monotonic()
    cached = _cache.get(normalized)
    if cached and now - cached[0] < _CACHE_SECONDS:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(
                f"{settings.photon_base_url.rstrip('/')}/api/",
                params={"q": query, "limit": max(1, min(limit, 8)), "lang": "en"},
                headers={"User-Agent": settings.nominatim_user_agent},
            )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return []

    results: list[GeocodedPlace] = []
    features = payload.get("features", []) if isinstance(payload, dict) else []
    for feature in features if isinstance(features, list) else []:
        try:
            properties = feature["properties"]
            coordinates = feature["geometry"]["coordinates"]
            name = _display_name(properties)
            if not name:
                continue
            osm_type = str(properties.get("osm_type", "place")).lower()
            osm_id = str(properties["osm_id"])
            feature_type = str(properties.get("type", properties.get("osm_value", ""))).casefold()
            zoom = {
                "country": 4.0,
                "state": 6.0,
                "county": 8.0,
                "city": 11.0,
                "town": 11.0,
                "village": 12.0,
                "district": 13.0,
                "street": 15.0,
                "house": 17.0,
            }.get(feature_type, 12.0)
            results.append(GeocodedPlace(
                place_id=f"photon-{osm_type}-{osm_id}",
                name=name,
                center=(float(coordinates[0]), float(coordinates[1])),
                provider="Photon / OpenStreetMap",
                zoom=zoom,
                bbox=tuple(float(value) for value in feature["bbox"]) if isinstance(feature.get("bbox"), list) and len(feature["bbox"]) == 4 else None,
            ))
        except (KeyError, TypeError, ValueError, IndexError):
            continue

    _cache[normalized] = (time.monotonic(), results)
    return results
