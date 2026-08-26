from datetime import date, timezone

import pytest

from app.adapters.gdacs import _map_feature, fetch_global_events
from app.core.config import Settings


def test_gdacs_feature_normalizes_operational_metadata():
    event = _map_feature({
        "geometry": {"type": "Point", "coordinates": [12.5, -7.1]},
        "properties": {
            "eventtype": "EQ",
            "eventid": 123,
            "name": "Earthquake in Test Region",
            "country": "Test Region",
            "alertlevel": "Orange",
            "alertscore": 1.8,
            "fromdate": "2026-07-16T12:00:00",
            "todate": "2026-07-16T12:00:00",
            "datemodified": "2026-07-16T12:30:00",
            "iscurrent": "true",
            "source": "NEIC",
            "severitydata": {"severitytext": "Magnitude 6.1M"},
            "url": {
                "report": "http://www.gdacs.org/report.aspx?eventid=123",
                "geometry": "https://www.gdacs.org/geometry/123",
            },
        },
    })
    assert event is not None
    assert event.event_id == "EQ-123"
    assert event.alert_level == "orange"
    assert event.center == (12.5, -7.1)
    assert event.modified_at.tzinfo == timezone.utc
    assert str(event.report_url).startswith("https://")


@pytest.mark.asyncio
async def test_gdacs_adapter_pages_and_deduplicates(monkeypatch):
    async def fake_get(_url, *, params):
        page = params["pagenumber"]
        if page > 2:
            return {"features": []}
        event_id = 100 + page
        duplicate = 101 if page == 2 else event_id
        return {
            "features": [{
                "geometry": {"type": "Point", "coordinates": [page, page]},
                "properties": {
                    "eventtype": "EQ", "eventid": duplicate, "name": f"Event {duplicate}",
                    "country": "Test", "alertlevel": "Green", "alertscore": 1,
                    "fromdate": "2026-07-16T12:00:00Z", "datemodified": "2026-07-16T12:30:00Z",
                    "url": {"report": f"https://www.gdacs.org/report.aspx?eventid={duplicate}"},
                },
            }]
        }

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    response = await fetch_global_events(Settings(), from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), force=True)
    assert len(response.items) == 1
    assert response.items[0].event_id == "EQ-101"
    assert "5 GDACS page(s)" in response.note
    assert response.request_params["fromDate"] == "2026-07-01"
    assert response.request_params["toDate"] == "2026-07-31"


@pytest.mark.asyncio
async def test_gdacs_adapter_serves_exact_cached_snapshot_when_refresh_fails(monkeypatch):
    calls = 0

    async def fake_get(_url, *, params):
        nonlocal calls
        calls += 1
        if calls > 5:
            return None
        return {"features": []}

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    settings = Settings()
    first = await fetch_global_events(settings, from_date=date(2026, 8, 1), to_date=date(2026, 8, 26), force=True)
    stale = await fetch_global_events(settings, from_date=date(2026, 8, 1), to_date=date(2026, 8, 26), force=True)
    assert first.status.value == "live"
    assert stale.status.value == "stale"
    assert "cached snapshot" in (stale.note or "")
