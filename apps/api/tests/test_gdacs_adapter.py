from datetime import timezone

from app.adapters.gdacs import _map_feature


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
