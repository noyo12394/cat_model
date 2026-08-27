from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.adapters.base import AdapterResponse
from app.adapters.gdacs import _map_feature
from app.main import app
from app.schemas.enums import DataStatus


client = TestClient(app)


def event(event_id: int, *, alert: str = "Green", country: str = "Japan"):
    mapped = _map_feature({
        "geometry": {"type": "Point", "coordinates": [139.7, 35.7]},
        "properties": {
            "eventtype": "EQ",
            "eventid": event_id,
            "name": f"Earthquake in {country}",
            "country": country,
            "alertlevel": alert,
            "alertscore": {"Green": 1, "Orange": 2, "Red": 3}[alert],
            "fromdate": "2026-07-16T12:00:00Z",
            "todate": "2026-07-16T12:00:00Z",
            "datemodified": "2026-07-16T12:30:00Z",
            "source": "NEIC",
            "url": {"report": f"https://www.gdacs.org/report.aspx?eventid={event_id}"},
        },
    })
    assert mapped is not None
    return mapped


def adapter_response(
    *,
    status: DataStatus,
    items: list,
    note: str,
    response_mode: str = "upstream",
) -> AdapterResponse:
    return AdapterResponse(
        source_name="GDACS",
        status=status,
        items=items,
        retrieved_at=datetime(2026, 8, 27, 4, 10, tzinfo=timezone.utc),
        note=note,
        source_url="https://www.gdacs.org/",
        request_url="https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH",
        request_params={
            "eventlist": "EQ",
            "alertlevel": "green;orange;red",
            "fromdate": "2026-07-01",
            "todate": "2026-07-31",
            "pagesize": 100,
            "pagenumber": 1,
        },
        response_mode=response_mode,
        snapshot_retrieved_at=(
            datetime(2026, 8, 27, 4, 10, tzinfo=timezone.utc)
            if response_mode == "checked_in_snapshot"
            else None
        ),
    )


def test_live_global_events_accepts_exact_from_to_and_composes_filters(monkeypatch):
    captured = {}

    async def fake_fetch(_settings, **kwargs):
        captured.update(kwargs)
        return adapter_response(
            status=DataStatus.LIVE,
            items=[event(301, alert="Green", country="Japan"), event(302, alert="Red", country="Indonesia")],
            note="2 official records returned.",
        )

    monkeypatch.setattr("app.api.v1.live.fetch_global_events", fake_fetch)
    response = client.get(
        "/api/v1/live/global-events",
        params={
            "from": "2026-07-01",
            "to": "2026-07-31",
            "hazard": "earthquake",
            "alert": "all",
            "region": "Indonesia",
            "q": "EQ-302",
            "min_impact": 3,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert captured["from_date"] == date(2026, 7, 1)
    assert captured["to_date"] == date(2026, 7, 31)
    assert captured["hazards"] == ("EQ",)
    assert captured["alerts"] == ("green", "orange", "red")
    assert [item["event_id"] for item in body["events"]] == ["EQ-302"]
    assert body["window_start"] == "2026-07-01"
    assert body["window_end"] == "2026-07-31"
    assert body["requested_window"] == "custom"
    assert body["query_parameters"]["fromdate"] == "2026-07-01"
    assert body["local_filters"]["region"] == "Indonesia"
    assert body["local_filters"]["min_impact"] == 3


def test_live_global_events_defaults_to_current_year_to_date(monkeypatch):
    captured = {}

    async def fake_fetch(_settings, **kwargs):
        captured.update(kwargs)
        return adapter_response(status=DataStatus.LIVE, items=[event(350)], note="One record.")

    monkeypatch.setattr("app.api.v1.live.fetch_global_events", fake_fetch)
    response = client.get("/api/v1/live/global-events")
    assert response.status_code == 200
    body = response.json()
    end = date.fromisoformat(body["window_end"])
    assert captured["from_date"] == date(end.year, 1, 1)
    assert captured["to_date"] == end
    assert body["requested_window"] == "ytd"


@pytest.mark.parametrize(
    ("status", "items", "mode", "expected_state"),
    [
        (DataStatus.LIVE, [], "upstream", "feed_ok_no_events"),
        (DataStatus.STALE, [event(401)], "checked_in_snapshot", "feed_degraded"),
        (DataStatus.UNAVAILABLE, [], "none", "feed_error"),
    ],
)
def test_live_global_events_has_explicit_feed_states(monkeypatch, status, items, mode, expected_state):
    async def fake_fetch(_settings, **_kwargs):
        return adapter_response(status=status, items=items, note="Source state detail.", response_mode=mode)

    monkeypatch.setattr("app.api.v1.live.fetch_global_events", fake_fetch)
    response = client.get(
        "/api/v1/live/global-events",
        params={"from": "2026-07-01", "to": "2026-07-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feed_state"] == expected_state
    assert body["feed_message"] == "Source state detail."
    assert body["stale"] is (status == DataStatus.STALE)
    assert body["error"] == ("Source state detail." if status == DataStatus.UNAVAILABLE else None)


def test_live_global_events_rejects_reversed_range_before_source_call(monkeypatch):
    async def should_not_run(*_args, **_kwargs):
        raise AssertionError("source should not be called for an invalid range")

    monkeypatch.setattr("app.api.v1.live.fetch_global_events", should_not_run)
    response = client.get(
        "/api/v1/live/global-events",
        params={"from": "2026-08-01", "to": "2026-07-01"},
    )
    assert response.status_code == 422
    assert "on or before" in response.json()["detail"]
