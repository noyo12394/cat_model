from fastapi.testclient import TestClient

from app.adapters.nominatim import GeocodedPlace
from app.api.v1 import places
from app.main import app


client = TestClient(app)


def test_unknown_address_uses_source_labelled_geocoder(monkeypatch):
    async def fake_geocode(query, settings, limit=5):
        assert query == "26 Warwick Road"
        return [GeocodedPlace(
            place_id="osm-way-123",
            name="26, Warwick Road, London, United Kingdom",
            center=(-0.1947, 51.4899),
        )]

    monkeypatch.setattr(places, "geocode_address", fake_geocode)
    response = client.get("/api/v1/places/search", params={"q": "26 Warwick Road"})
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["provider"] == "OpenStreetMap Nominatim"
    assert result["data_status"] == "live"
    assert result["center"] == [-0.1947, 51.4899]


def test_seeded_place_does_not_call_external_geocoder(monkeypatch):
    async def fail_geocode(*args, **kwargs):
        raise AssertionError("external geocoder should not run for seeded places")

    monkeypatch.setattr(places, "geocode_address", fail_geocode)
    response = client.get("/api/v1/places/search", params={"q": "Lehigh University"})
    assert response.status_code == 200
    assert response.json()["results"][0]["provider"] == "RiskChain place directory"


def test_suggestions_merge_local_and_source_labelled_photon(monkeypatch):
    async def fake_suggest(query, settings, limit=6):
        assert query == "New Jer"
        return [GeocodedPlace(
            place_id="photon-r-224951",
            name="New Jersey, United States",
            center=(-74.4041622, 40.0757384),
            provider="Photon / OpenStreetMap",
        )]

    monkeypatch.setattr(places, "suggest_geocoded_places", fake_suggest)
    response = client.get("/api/v1/places/suggest", params={"q": "New Jer"})
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["name"] == "New Jersey, United States"
    assert result["provider"] == "Photon / OpenStreetMap"
    assert result["center"] == [-74.4041622, 40.0757384]
