from datetime import datetime, timedelta, timezone

from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent
from app.services.assistant import _requested_horizon
from app.services.global_outlook import horizon_label, priority_for


def _event(level: str, score: float, modified_at: datetime) -> GlobalEvent:
    return GlobalEvent(
        event_id="EQ-test",
        event_type="EQ",
        name="Test earthquake",
        country="Test country",
        alert_level=level,
        alert_score=score,
        severity_text="M 6.0",
        from_date=modified_at,
        to_date=modified_at,
        modified_at=modified_at,
        center=(12.4, 8.9),
        source="GDACS",
        report_url="https://www.gdacs.org/report.aspx?eventid=test",
        data_status=DataStatus.LIVE,
    )


def test_watch_priority_is_alert_and_freshness_triage_not_probability():
    now = datetime(2026, 7, 16, 16, tzinfo=timezone.utc)
    red = priority_for(_event("red", 2.0, now - timedelta(minutes=20)), 15, now=now)
    green = priority_for(_event("green", 0.0, now - timedelta(days=2)), 15, now=now)

    assert red.priority_score > green.priority_score
    assert red.priority_label == "Immediate verification"
    assert "Verify the official report" in red.next_action
    assert "GDACS red alert" in red.drivers


def test_horizon_labels_are_human_readable():
    assert horizon_label(0) == "Current operating picture"
    assert horizon_label(15) == "Next 15 minutes"
    assert horizon_label(360) == "Next 6 hours"


def test_agent_reads_the_selected_global_operating_window():
    assert _requested_horizon("Give a global GDACS brief for a 0-minute operating window") == 0
    assert _requested_horizon("Give a global GDACS brief for the next 6 hours") == 360
