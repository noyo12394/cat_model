from __future__ import annotations

import pytest

from app.core.config import Settings
from app.schemas.analysis import AnalysisHazard
from app.services.cat import hazard_providers


@pytest.mark.asyncio
async def test_usgs_event_detail_uses_fdsn_for_regional_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_get(url: str, params: dict[str, str]) -> dict[str, object]:
        captured.update(url=url, params=params)
        return {"properties": {"title": "M 7.1 - Ridgecrest Earthquake Sequence", "products": {"shakemap": []}}}

    monkeypatch.setattr(hazard_providers, "safe_get_json", fake_get)
    provider = hazard_providers.USGSEarthquakeProvider(Settings())

    detail = await provider.get_event_details("ci38457511")

    assert captured["url"] == "https://earthquake.usgs.gov/fdsnws/event/1/query"
    assert captured["params"] == {"eventid": "ci38457511", "format": "geojson"}
    assert detail["properties"]["title"] == "M 7.1 - Ridgecrest Earthquake Sequence"


_NWS_FLOOD_ALERT = {
    "type": "Feature",
    "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.demo-flood.001.1",
    "properties": {
        "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.demo-flood.001.1",
        "id": "urn:oid:2.49.0.1.840.0.demo-flood.001.1",
        "event": "Flood Warning",
        "headline": "Flood Warning issued by NWS Test Office",
        "status": "Actual",
        "effective": "2026-07-23T12:00:00+00:00",
        "sent": "2026-07-23T12:05:00+00:00",
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-75.5, 40.5], [-75.4, 40.5], [-75.4, 40.6], [-75.5, 40.5]]],
    },
}


@pytest.mark.asyncio
async def test_nws_flood_alert_provider_exposes_only_official_alert_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        if url.endswith("/active"):
            return {"type": "FeatureCollection", "features": [_NWS_FLOOD_ALERT] if params == {"event": "Flood Warning"} else []}
        return _NWS_FLOOD_ALERT

    monkeypatch.setattr(hazard_providers, "safe_get_json", fake_get)
    provider = hazard_providers.NWSFloodAlertProvider()

    response = await provider.get_active_events()

    assert response.data_status == "live"
    assert response.provider == "National Weather Service"
    assert len(response.events) == 1
    assert response.events[0].hazard_type == AnalysisHazard.FLOOD
    assert response.events[0].footprint_available is True
    assert "alert area" in response.events[0].limitations[0].lower()
    assert await provider.get_hazard_footprint(response.events[0].provider_event_id, "NWS alert-area polygon") == [_NWS_FLOOD_ALERT]


@pytest.mark.asyncio
async def test_nws_flood_alert_provider_rejects_non_nws_event_urls() -> None:
    provider = hazard_providers.NWSFloodAlertProvider()
    assert await provider.get_hazard_footprint("https://not-the-weather-service.example/alerts/1", "NWS alert-area polygon") == []
