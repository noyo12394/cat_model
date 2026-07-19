from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.usgs_water import _map_feature
from app.main import app


def test_source_registry_exposes_governance_fields():
    response = TestClient(app).get("/api/v1/sources/registry")
    assert response.status_code == 200
    records = {record["key"]: record for record in response.json()}
    assert set(records) >= {"NWS", "USGS_WATER", "GDACS", "X_COMMUNITY"}
    assert records["USGS_WATER"]["docs_url"].startswith("https://api.waterdata.usgs.gov/")
    assert records["X_COMMUNITY"]["commercial_use_status"] == "licensed_restricted"
    assert all(record["verified_at"] == "2026-07-18" for record in records.values())


def test_modern_usgs_water_feature_preserves_provisional_status():
    observation = _map_feature({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-75.2, 40.6]},
        "properties": {
            "monitoring_location_id": "USGS-01452500",
            "time": "2026-07-18T12:00:00+00:00",
            "value": "4.27",
            "unit_of_measure": "ft",
            "approval_status": "Provisional",
        },
    })
    assert observation is not None
    assert observation.sensor_id == "01452500"
    assert observation.value == 4.27
    assert "Provisional" in observation.quality_flags[0]
    assert observation.provenance.data_status.value == "live"
