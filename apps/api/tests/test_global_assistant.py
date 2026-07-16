from datetime import datetime, timezone

import pytest

from app.adapters.base import AdapterResponse
from app.core.config import Settings
from app.schemas.assistant import AssistantContext
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent
from app.services.assistant import answer_question_async


def _event(event_id: str, name: str, country: str, alert_level: str, score: float) -> GlobalEvent:
    observed_at = datetime(2026, 7, 16, 17, tzinfo=timezone.utc)
    return GlobalEvent(
        event_id=event_id,
        event_type="EQ",
        name=name,
        country=country,
        alert_level=alert_level,
        alert_score=score,
        severity_text="Magnitude 5.2M",
        from_date=observed_at,
        to_date=observed_at,
        modified_at=observed_at,
        center=(12.0, 8.0),
        source="NEIC",
        report_url=f"https://www.gdacs.org/report.aspx?eventid={event_id}",
        data_status=DataStatus.LIVE,
    )


@pytest.mark.asyncio
async def test_global_context_routes_plain_language_earthquake_question(monkeypatch, repo):
    events = [_event(f"EQ-{index}", f"Earthquake {index}", f"Place {index}", "orange" if index == 1 else "green", 2.0) for index in range(1, 7)]

    async def fake_fetch(_settings):
        return AdapterResponse(source_name="GDACS", status=DataStatus.LIVE, items=events, note="live")

    monkeypatch.setattr("app.services.assistant.fetch_global_events", fake_fetch)
    answer = await answer_question_async(
        repo,
        Settings(),
        "five places with most risks of earthquakes",
        context=AssistantContext(scope="global", horizon_minutes=0),
    )

    assert "does not yet have a global place-risk" in answer.answer
    assert "Earthquake 1" in answer.answer
    assert "Earthquake 5" in answer.answer
    assert "Earthquake 6" not in answer.answer
    assert answer.location_label == "Global operating picture"
    assert answer.tool_trace[0].tool == "gdacs_global_event_intake"
