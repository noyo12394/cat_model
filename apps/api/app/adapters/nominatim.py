"""Low-volume, submit-only OpenStreetMap Nominatim geocoding adapter.

The public service permits light interactive searches when clients identify
themselves, stay below one request per second, cache results, and do not build
autocomplete. RiskChain calls this adapter only after an explicit form submit.
It is a replaceable fallback until a licensed production geocoder is present.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from app.core.config import Settings


@dataclass(frozen=True)
class GeocodedPlace:
    place_id: str
    name: str
    center: tuple[float, float]
    provider: str = "OpenStreetMap Nominatim"
    data_status: str = "live"
    zoom: float = 12.0
    bbox: tuple[float, float, float, float] | None = None


_cache: dict[str, tuple[float, list[GeocodedPlace]]] = {}
_lock = asyncio.Lock()
_last_request_at = 0.0
_CACHE_SECONDS = 900.0


async def geocode_address(query: str, settings: Settings, limit: int = 5) -> list[GeocodedPlace]:
    """Return real provider results or an empty list; never synthetic matches."""
    normalized = " ".join(query.split()).casefold()
    if not normalized:
        return []
    now = time.monotonic()
    cached = _cache.get(normalized)
    if cached and now - cached[0] < _CACHE_SECONDS:
        return cached[1]

    global _last_request_at
    async with _lock:
        cached = _cache.get(normalized)
        now = time.monotonic()
        if cached and now - cached[0] < _CACHE_SECONDS:
            return cached[1]
        remaining = 1.0 - (now - _last_request_at)
        if remaining > 0:
            await asyncio.sleep(remaining)
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"{settings.nominatim_base_url.rstrip('/')}/search",
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "limit": max(1, min(limit, 5)),
                    },
                    headers={
                        "User-Agent": settings.nominatim_user_agent,
                        "Accept-Language": "en",
                    },
                )
            _last_request_at = time.monotonic()
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            return []

        results: list[GeocodedPlace] = []
        for item in payload if isinstance(payload, list) else []:
            try:
                osm_type = str(item.get("osm_type", "place"))
                osm_id = str(item["osm_id"])
                address_type = str(item.get("addresstype", item.get("type", ""))).casefold()
                zoom = {
                    "country": 4.0,
                    "state": 6.0,
                    "region": 7.0,
                    "county": 8.0,
                    "city": 11.0,
                    "town": 11.0,
                    "village": 12.0,
                    "postcode": 12.0,
                    "road": 15.0,
                    "house": 17.0,
                    "building": 17.0,
                }.get(address_type, 12.0)
                results.append(GeocodedPlace(
                    place_id=f"osm-{osm_type}-{osm_id}",
                    name=str(item["display_name"]),
                    center=(float(item["lon"]), float(item["lat"])),
                    zoom=zoom,
                    bbox=(float(item["boundingbox"][2]), float(item["boundingbox"][0]), float(item["boundingbox"][3]), float(item["boundingbox"][1])) if isinstance(item.get("boundingbox"), list) and len(item["boundingbox"]) == 4 else None,
                ))
            except (KeyError, TypeError, ValueError):
                continue
        _cache[normalized] = (time.monotonic(), results)
        return results
