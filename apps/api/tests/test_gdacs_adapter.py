from datetime import date, timezone

import pytest

from app.adapters.gdacs import _map_feature, fetch_global_events
from app.core.config import Settings


def gdacs_feature(
    event_id: int,
    *,
    event_type: str = "EQ",
    alert: str = "Green",
    country: str = "Test",
    from_date: str = "2026-07-16T12:00:00Z",
) -> dict:
    return {
        "geometry": {"type": "Point", "coordinates": [event_id % 90, event_id % 45]},
        "properties": {
            "eventtype": event_type,
            "eventid": event_id,
            "name": f"{event_type} Event {event_id}",
            "country": country,
            "alertlevel": alert,
            "alertscore": {"Green": 1, "Orange": 2, "Red": 3}[alert],
            "fromdate": from_date,
            "todate": from_date,
            "datemodified": from_date,
            "url": {"report": f"https://www.gdacs.org/report.aspx?eventid={event_id}"},
        },
    }


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
        return {"features": [gdacs_feature(101)]} if page <= 2 else {"features": []}

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    monkeypatch.setattr("app.adapters.gdacs._PAGE_SIZE", 1)
    response = await fetch_global_events(Settings(), from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), force=True)
    assert len(response.items) == 1
    assert response.items[0].event_id == "EQ-101"
    assert "3 GDACS page(s)" in response.note
    assert response.request_params["fromdate"] == "2026-07-01"
    assert response.request_params["todate"] == "2026-07-31"


@pytest.mark.asyncio
async def test_gdacs_adapter_marks_failed_later_page_as_partial(monkeypatch):
    async def fake_get(_url, *, params):
        return {"features": [gdacs_feature(150)]} if params["pagenumber"] == 1 else None

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    monkeypatch.setattr("app.adapters.gdacs._PAGE_SIZE", 1)
    response = await fetch_global_events(
        Settings(),
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
        force=True,
    )
    assert response.status.value == "stale"
    assert response.response_mode == "partial_upstream"
    assert response.items[0].data_status.value == "stale"
    assert "page 2" in (response.note or "")


@pytest.mark.asyncio
async def test_gdacs_adapter_serves_exact_cached_snapshot_when_refresh_fails(monkeypatch):
    available = True

    async def fake_get(_url, *, params):
        return {"features": []} if available else None

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    settings = Settings()
    first = await fetch_global_events(settings, from_date=date(2026, 8, 1), to_date=date(2026, 8, 26), force=True)
    available = False
    stale = await fetch_global_events(settings, from_date=date(2026, 8, 1), to_date=date(2026, 8, 26), force=True)
    assert first.status.value == "live"
    assert stale.status.value == "stale"
    assert "memory cache" in (stale.note or "")


@pytest.mark.asyncio
async def test_gdacs_adapter_uses_compatible_broad_cache_for_filtered_query(monkeypatch):
    available = True

    async def fake_get(_url, *, params):
        if not available:
            return None
        return {
            "features": [
                gdacs_feature(201, event_type="EQ", alert="Green", country="Japan"),
                gdacs_feature(202, event_type="TC", alert="Red", country="Mexico"),
            ]
        }

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    settings = Settings()
    broad = await fetch_global_events(
        settings,
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
        force=True,
    )
    available = False
    filtered = await fetch_global_events(
        settings,
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
        hazards=("EQ",),
        alerts=("green",),
        force=True,
    )
    assert broad.status.value == "live"
    assert filtered.status.value == "stale"
    assert [event.event_id for event in filtered.items] == ["EQ-201"]
    assert filtered.items[0].data_status.value == "stale"


@pytest.mark.asyncio
async def test_gdacs_adapter_cold_start_snapshot_is_real_filtered_and_labelled(monkeypatch):
    async def unavailable(_url, *, params):
        return None

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", unavailable)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    response = await fetch_global_events(
        Settings(),
        from_date=date(2026, 7, 1),
        to_date=date(2026, 8, 27),
        hazards=("WF",),
        alerts=("red",),
        force=True,
    )
    assert response.status.value == "stale"
    assert response.response_mode == "checked_in_snapshot"
    assert response.snapshot_retrieved_at is not None
    assert [event.event_id for event in response.items] == ["WF-1029628"]
    assert response.items[0].data_status.value == "stale"
    assert "Coverage may be partial" in (response.note or "")


@pytest.mark.asyncio
async def test_gdacs_adapter_serves_cold_snapshot_before_calling_upstream(monkeypatch):
    calls = 0

    async def should_not_run(_url, *, params):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", should_not_run)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    response = await fetch_global_events(
        Settings(),
        from_date=date(2026, 7, 1),
        to_date=date(2026, 8, 27),
        hazards=("WF",),
        alerts=("red",),
    )
    assert calls == 0
    assert response.status.value == "stale"
    assert response.response_mode == "checked_in_snapshot"
    assert [event.event_id for event in response.items] == ["WF-1029628"]
    assert "scheduled feed warmer" in (response.note or "")


@pytest.mark.asyncio
async def test_gdacs_adapter_reports_unavailable_outside_snapshot_coverage(monkeypatch):
    async def unavailable(_url, *, params):
        return None

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", unavailable)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    response = await fetch_global_events(
        Settings(),
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        force=True,
    )
    assert response.status.value == "unavailable"
    assert response.response_mode == "none"
    assert response.items == []
