from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_search_place_and_get_capsule():
    search = client.get("/api/v1/places/search", params={"q": "Lehigh University"})
    assert search.status_code == 200
    results = search.json()["results"]
    assert results and results[0]["place_id"] == "lehigh-university"

    capsule = client.get(f"/api/v1/places/{results[0]['place_id']}/capsule")
    assert capsule.status_code == 200
    body = capsule.json()
    assert body["data_confidence"] in ("low", "moderate", "high")
    assert "last_updated" in body


def test_incident_flow_timeline_forecast_evidence():
    incidents = client.get("/api/v1/incidents").json()
    assert len(incidents) == 1
    incident_id = incidents[0]["incident_id"]

    timeline = client.get(f"/api/v1/incidents/{incident_id}/timeline").json()
    assert len(timeline["timeline"]) >= 5

    forecast = client.get(f"/api/v1/incidents/{incident_id}/forecast").json()
    assert forecast["steps"], "expected at least one 'what may happen next' step"
    for step in forecast["steps"]:
        assert step["confidence"] in ("low", "moderate", "high")
        assert step["evidence_trail"]["weaknesses"], "every AI step must disclose a limitation"

    evidence = client.get(f"/api/v1/incidents/{incident_id}/evidence").json()
    assert len(evidence) >= 1


def test_route_analyze_never_says_safe():
    resp = client.post(
        "/api/v1/routes/analyze",
        json={"origin_place_id": "lehigh-university", "destination_place_id": "fac-stlukes-bethlehem"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["options"]) == 3
    assert "no route is guaranteed safe" in body["disclaimer"].lower()
    for opt in body["options"]:
        assert opt["exposure_level"] in ("lower", "elevated", "unavailable")


def test_scenario_create_run_and_fetch_results():
    created = client.post("/api/v1/scenarios", json={"name": "test scenario", "actions": []})
    assert created.status_code == 200
    scenario_id = created.json()["scenario_id"]

    run = client.post(f"/api/v1/scenarios/{scenario_id}/run")
    assert run.status_code == 200

    fetched = client.get(f"/api/v1/scenarios/{scenario_id}/results")
    assert fetched.status_code == 200
    assert fetched.json()["scenario_id"] == scenario_id


def test_scenario_results_404_before_run():
    created = client.post("/api/v1/scenarios", json={"name": "no run yet"})
    scenario_id = created.json()["scenario_id"]
    fetched = client.get(f"/api/v1/scenarios/{scenario_id}/results")
    assert fetched.status_code == 404


def test_assistant_query_always_includes_confidence_and_time_range():
    resp = client.post("/api/v1/assistant/query", json={"question": "Why is this area uncertain?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["confidence"] in ("low", "moderate", "high")
    assert body["time_range"]["label"]


def test_hidden_risks_returns_ranked_list():
    resp = client.get("/api/v1/risks/hidden")
    assert resp.status_code == 200
    risks = resp.json()
    assert risks
    ranks = [r["severity_rank"] for r in risks]
    assert ranks == sorted(ranks)


def test_source_health_lists_all_registered_sources():
    resp = client.get("/api/v1/sources/status")
    assert resp.status_code == 200
    keys = {s["key"] for s in resp.json()}
    assert "NWS" in keys and "USGS_WATER" in keys


def test_model_card_not_found_returns_404():
    resp = client.get("/api/v1/models/does-not-exist/card")
    assert resp.status_code == 404
