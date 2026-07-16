"""Google Maps Platform server-side adapter (Places + Routes proxying).

Per section 44 (cost controls) and section 40 (security), the browser never
calls Places/Routes directly with a server key - the backend proxies those
calls so credentials stay server-side and responses can be cached. Without
``GOOGLE_MAPS_SERVER_API_KEY`` configured, Route Risk analysis falls back to
EarthPulse's own demo route graph (see services/route_risk.py), which is
real routing logic (not invented data) over the seeded facility/road
fixtures - it just isn't Google's live traffic-aware routing.

Env vars: ``GOOGLE_MAPS_SERVER_API_KEY``. The frontend separately uses
``NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`` (a browser-restricted key) for the map
tiles themselves; see apps/web/README.md.
"""

from __future__ import annotations

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus


async def compute_route_google(
    settings: Settings, origin: tuple[float, float], destination: tuple[float, float]
) -> AdapterResponse[dict]:
    if not settings.google_maps_server_api_key:
        return AdapterResponse(
            source_name="GOOGLE_ROUTES",
            status=DataStatus.UNAVAILABLE,
            items=[],
            note="GOOGLE_MAPS_SERVER_API_KEY not configured; using EarthPulse demo route graph.",
        )
    body = {
        "origin": {"location": {"latLng": {"latitude": origin[1], "longitude": origin[0]}}},
        "destination": {
            "location": {"latLng": {"latitude": destination[1], "longitude": destination[0]}}
        },
        "travelMode": "DRIVE",
    }
    payload = await safe_get_json(
        "https://routes.googleapis.com/directions/v2:computeRoutes", body
    )
    if payload:
        return AdapterResponse(source_name="GOOGLE_ROUTES", status=DataStatus.LIVE, items=[payload])
    return AdapterResponse(
        source_name="GOOGLE_ROUTES",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note="Google Routes API call failed; using EarthPulse demo route graph.",
    )
