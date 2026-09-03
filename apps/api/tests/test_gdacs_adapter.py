from datetime import date, timezone

import pytest

from app.adapters.gdacs import _RECENT_FEED_URL, _map_feature, fetch_global_events, request_params
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
    async def fake_get(url, *, params):
        if url == _RECENT_FEED_URL:
            return None
        page = params["pagenumber"]
        return {"features": [gdacs_feature(101)]} if page <= 2 else {"features": []}

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    monkeypatch.setattr("app.adapters.gdacs._PAGE_SIZE", 1)
    response = await fetch_global_events(Settings(), from_date=date(2026, 7, 1), to_date=date(2026, 7, 31), force=True)
    assert len(response.items) == 1
    assert response.items[0].event_id == "EQ-101"
    assert "1 GDACS page(s)" in response.note
    assert response.request_params["fromdate"] == "2026-07-01"
    assert response.request_params["todate"] == "2026-07-31"
    assert "eventlist" not in response.request_params
    assert "alertlevel" not in response.request_params


@pytest.mark.asyncio
async def test_gdacs_adapter_marks_failed_later_page_as_partial(monkeypatch):
    async def fake_get(url, *, params):
        if url == _RECENT_FEED_URL:
            return None
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

    async def fake_get(url, *, params):
        if url == _RECENT_FEED_URL:
            return None
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

    async def fake_get(url, *, params):
        if url == _RECENT_FEED_URL:
            return None
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
async def test_gdacs_adapter_checks_fast_feed_then_serves_cold_snapshot_without_search(monkeypatch):
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
    assert calls == 1
    assert response.status.value == "stale"
    assert response.response_mode == "checked_in_snapshot"
    assert [event.event_id for event in response.items] == ["WF-1029628"]
    assert "scheduled feed warmer" in (response.note or "")


def test_gdacs_search_request_never_uses_semicolon_filters():
    params = request_params(
        date(2026, 8, 28),
        date(2026, 9, 3),
        ("EQ", "TC"),
        ("green", "red"),
        1,
    )
    assert params == {
        "fromdate": "2026-08-28",
        "todate": "2026-09-03",
        "pagesize": 100,
        "pagenumber": 1,
    }


@pytest.mark.asyncio
async def test_recent_application_feed_returns_without_search_pagination(monkeypatch):
    calls: list[tuple[str, dict]] = []

    async def fake_get(url, *, params):
        calls.append((url, params))
        assert url == _RECENT_FEED_URL
        return {"features": [gdacs_feature(901, from_date="2026-09-03T10:00:00Z")]}

    monkeypatch.setattr("app.adapters.gdacs.safe_get_json", fake_get)
    monkeypatch.setattr("app.adapters.gdacs._cache", {})
    response = await fetch_global_events(
        Settings(),
        from_date=date(2026, 9, 3),
        to_date=date(2026, 9, 3),
        force=True,
    )
    assert response.status.value == "live"
    assert response.response_mode == "upstream"
    assert [event.event_id for event in response.items] == ["EQ-901"]
    assert calls == [(_RECENT_FEED_URL, {})]


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
