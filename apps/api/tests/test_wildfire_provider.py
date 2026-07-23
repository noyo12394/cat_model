"""NIFC wildfire provider: authoritative perimeters, screening only, no loss."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.adapters import nifc
from app.api.v1 import analysis
from app.core.config import Settings
from app.schemas.analysis import (
    AnalysisHazard,
    AnalysisRunRequest,
    AnalysisTotals,
    SourceRecord,
)
from app.services.cat.hazard_providers import provider_for
from app.services.cat.wildfire_provider import NIFCWildfireProvider

# One ArcGIS ``f=json`` feature (list) and one ``f=geojson`` feature (footprint).
_LIST_PAYLOAD = {
    "features": [
        {
            "attributes": {
                "attr_UniqueFireIdentifier": "2026-CACDD-001234",
                "attr_IncidentName": "RIDGE",
                "attr_IncidentSize": 18450.0,
                "attr_PercentContained": 35.0,
                "attr_FireDiscoveryDateTime": 1_753_000_000_000,
                "attr_ModifiedOnDateTime_dt": 1_753_500_000_000,
                "attr_POOState": "US-CA",
                "attr_IncidentTypeCategory": "WF",
                "attr_FireCause": "Natural",
            },
            "centroid": {"x": -120.5, "y": 39.1},
        }
    ]
}
_GEOJSON_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"attr_UniqueFireIdentifier": "2026-CACDD-001234"},
            "geometry": {"type": "Polygon", "coordinates": [[[-121, 39], [-120, 39], [-120, 40], [-121, 39]]]},
        }
    ],
}


def _stub(monkeypatch, list_payload=_LIST_PAYLOAD, geojson_payload=_GEOJSON_PAYLOAD):
    async def fake_get_json(url, params=None, headers=None, **_):
        return geojson_payload if params and params.get("f") == "geojson" else list_payload

    monkeypatch.setattr(nifc, "safe_get_json", fake_get_json)


def test_provider_for_wildfire_is_wired():
    assert isinstance(provider_for(AnalysisHazard.WILDFIRE, Settings()), NIFCWildfireProvider)


@pytest.mark.asyncio
async def test_active_events_are_observed_perimeters(monkeypatch):
    _stub(monkeypatch)
    response = await NIFCWildfireProvider().get_active_events()
    assert response.data_status == "live" and len(response.events) == 1
    event = response.events[0]
    assert event.hazard_type == AnalysisHazard.WILDFIRE
    assert event.classification == "observed"  # a mapped boundary, not a forecast
    assert event.footprint_available is True
    assert event.center == (-120.5, 39.1)
    assert event.name == "Ridge"  # ALL-CAPS incident names are title-cased
    assert "18,450 acres" in event.status and "35% contained" in event.status


@pytest.mark.asyncio
async def test_service_outage_is_unavailable_not_calm(monkeypatch):
    async def fake_get_json(url, params=None, headers=None, **_):
        return None

    monkeypatch.setattr(nifc, "safe_get_json", fake_get_json)
    response = await NIFCWildfireProvider().get_active_events()
    assert response.data_status == "unavailable" and not response.events
    assert "unavailable" in (response.message or "").lower()


@pytest.mark.asyncio
async def test_footprint_returns_authoritative_geometry(monkeypatch):
    _stub(monkeypatch)
    footprint = await NIFCWildfireProvider().get_hazard_footprint("2026-CACDD-001234", "any")
    assert len(footprint) == 1 and footprint[0]["geometry"]["type"] == "Polygon"


@pytest.mark.asyncio
async def test_perimeter_fetch_gets_source_specific_timeout(monkeypatch):
    received: dict = {}

    async def fake_get_json(url, params=None, headers=None, **kwargs):
        received.update(kwargs)
        return _GEOJSON_PAYLOAD

    monkeypatch.setattr(nifc, "safe_get_json", fake_get_json)
    await nifc.fetch_wildfire_perimeter_geometry("2026-CACDD-001234")
    assert received["timeout"] == 20.0


@pytest.mark.asyncio
async def test_footprint_rejects_injection_style_id(monkeypatch):
    _stub(monkeypatch)
    # A value that is not a clean fire identifier is refused before any query.
    assert await NIFCWildfireProvider().get_hazard_footprint("' OR 1=1 --", "any") == []


@pytest.mark.asyncio
async def test_historical_is_honestly_unavailable():
    response = await NIFCWildfireProvider().search_historical_events(date(2026, 1, 1), date(2026, 6, 1))
    assert response.data_status == "unavailable" and not response.events


@pytest.mark.asyncio
async def test_wildfire_analysis_is_screening_and_never_loss(monkeypatch):
    _stub(monkeypatch)

    async def fake_screening(footprints):
        assert footprints and footprints[0]["geometry"]["type"] == "Polygon"
        return {
            "sources": [SourceRecord(dataset="National Structure Inventory 2026 Base", provider="USACE", url="https://nsi.sec.usace.army.mil", version="2026 Base", retrieved_at=datetime.now(timezone.utc), status="loaded")],
            "totals": AnalysisTotals(structures=27, population=61, structure_value_usd=4_100_000, excluded_assets=27),
            "limitations": ["No asset-level fire intensity is available."],
        }

    monkeypatch.setattr(analysis, "run_polygon_exposure_screening", fake_screening)
    result = await analysis.create_analysis(
        AnalysisRunRequest(mode="live", hazard_type="wildfire", event_id="2026-CACDD-001234", provider="NIFC"),
        Settings(),
    )
    assert result.result_type == "exposure_screening" and result.loss is None
    assert result.component_status["hazard"] == "loaded" and result.component_status["exposure"] == "loaded"
    assert result.totals.structures == 27
    assert result.manifest.excluded_records["no_compatible_intensity"] == 27
    # The authoritative perimeter must be recorded as a source of the screening.
    assert any("Fire Center" in source.provider for source in result.manifest.sources)
