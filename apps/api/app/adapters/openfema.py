"""OpenFEMA adapter: official disaster declarations for historical context.

Real endpoint: {OPENFEMA_BASE_URL}/v2/DisasterDeclarationsSummaries - no API
key required. Used to ground the Historical Analog Finder in real
declarations rather than only synthetic composites, when reachable.
"""

from __future__ import annotations

from app.adapters.base import AdapterResponse, safe_get_json
from app.core.config import Settings
from app.schemas.enums import DataStatus


async def fetch_disaster_declarations(
    settings: Settings, state: str = "PA", limit: int = 10
) -> AdapterResponse[dict]:
    payload = await safe_get_json(
        f"{settings.openfema_base_url}/v2/DisasterDeclarationsSummaries",
        {
            "$filter": f"state eq '{state}' and incidentType eq 'Flood'",
            "$top": str(limit),
            "$orderby": "declarationDate desc",
        },
    )
    if payload and isinstance(payload, dict) and payload.get("DisasterDeclarationsSummaries"):
        return AdapterResponse(
            source_name="OPENFEMA",
            status=DataStatus.LIVE,
            items=payload["DisasterDeclarationsSummaries"],
        )
    return AdapterResponse(
        source_name="OPENFEMA",
        status=DataStatus.UNAVAILABLE,
        items=[],
        note="Live OpenFEMA feed unavailable; historical analogs use the seeded demo composites only.",
    )
