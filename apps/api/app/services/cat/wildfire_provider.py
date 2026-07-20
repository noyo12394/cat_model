"""NIFC wildfire hazard provider.

Implements the same ``HazardProvider`` protocol as the hurricane and earthquake
providers so the analysis service can screen exposure inside an official
wildfire perimeter without any special-casing. Perimeters are observed mapped
boundaries; this provider therefore only ever produces an *exposure screening*
- membership inside the fire boundary - and never a damage or dollar loss.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.adapters.nifc import (
    NIFC_SOURCE_URL,
    fetch_active_wildfire_perimeters,
    fetch_wildfire_perimeter_geometry,
)
from app.schemas.analysis import HazardEventSearchResponse, HazardEventSummary

_CONTAINED_NOTE = "Perimeter is a mapped fire boundary, not a hazard-intensity surface. Exposure is screening only."


class NIFCWildfireProvider:
    """Authoritative current wildfire perimeters from NIFC WFIGS."""

    async def get_active_events(self) -> HazardEventSearchResponse:
        retrieved_at = datetime.now(timezone.utc)
        perimeters = await fetch_active_wildfire_perimeters()
        if perimeters is None:
            return HazardEventSearchResponse(
                events=[],
                provider="National Interagency Fire Center",
                retrieved_at=retrieved_at,
                data_status="unavailable",
                message="The NIFC wildfire-perimeter service is unavailable; no substitute fire is shown.",
            )
        events: list[HazardEventSummary] = []
        for perimeter in perimeters:
            acres = f"{perimeter.acres:,.0f} acres" if perimeter.acres else "size not reported"
            contained = (
                f", {perimeter.percent_contained:.0f}% contained"
                if perimeter.percent_contained is not None
                else ""
            )
            events.append(
                HazardEventSummary(
                    provider="NIFC",
                    provider_event_id=perimeter.event_id,
                    hazard_type="wildfire",
                    name=perimeter.name.title() if perimeter.name.isupper() else perimeter.name,
                    status=f"{acres}{contained}",
                    start_time=perimeter.discovered_at,
                    update_time=perimeter.modified_at,
                    center=perimeter.center,
                    source_url=NIFC_SOURCE_URL,
                    source_version=perimeter.modified_at.isoformat() if perimeter.modified_at else "current perimeters",
                    classification="observed",
                    footprint_available=True,
                    limitations=[_CONTAINED_NOTE],
                )
            )
        message = None if events else "No active interagency wildfire perimeter is currently mapped."
        return HazardEventSearchResponse(
            events=events,
            provider="National Interagency Fire Center",
            retrieved_at=retrieved_at,
            data_status="live",
            message=message,
        )

    async def search_historical_events(self, start: date, end: date) -> HazardEventSearchResponse:
        return HazardEventSearchResponse(
            events=[],
            provider="National Interagency Fire Center",
            retrieved_at=datetime.now(timezone.utc),
            data_status="unavailable",
            message="Only current-year perimeters are connected. The historical fire-perimeter archive is not wired up in this release.",
        )

    async def get_event_details(self, event_id: str, advisory_id: str | None = None) -> dict:
        response = await self.get_active_events()
        event = next((item for item in response.events if item.provider_event_id == event_id), None)
        if not event:
            return {}
        return {"properties": {"title": event.name}, "event": event.model_dump(mode="json")}

    async def get_hazard_footprint(self, event_id: str, threshold: str) -> list[dict]:
        # A perimeter has no intensity threshold; the mapped boundary itself is
        # the footprint used for exposure screening.
        return await fetch_wildfire_perimeter_geometry(event_id)

    def get_source_metadata(self) -> dict:
        return {"provider": "National Interagency Fire Center (WFIGS)", "url": NIFC_SOURCE_URL}
