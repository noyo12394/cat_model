from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse
from app.adapters.x_community import CommunityPost, classify_community_language
from app.schemas.enums import DataStatus
from app.schemas.global_event import GlobalEvent
from app.services.community_signals import build_community_signals


def _event() -> GlobalEvent:
    now = datetime(2026, 7, 16, 18, tzinfo=timezone.utc)
    return GlobalEvent(
        event_id="GDACS-FL-1",
        event_type="FL",
        name="Flood in Testland",
        country="Testland",
        alert_level="orange",
        severity_text="Test event",
        from_date=now,
        to_date=now,
        modified_at=now,
        center=(12.4, 43.2),
        source="GDACS",
        report_url="https://www.gdacs.org/",
    )


def test_community_language_labels_are_explicit_and_do_not_claim_verification():
    tone, report_type, tags = classify_community_language("Help — the bridge road is closed and flooding is rising.")
    assert tone == "urgent_language"
    assert report_type == "possible_impact_report"
    assert "flooding" in tags
    assert "road access" in tags


def test_unconfigured_source_never_generates_demo_sentiment():
    result = build_community_signals(
        _event(),
        AdapterResponse("X API", DataStatus.UNAVAILABLE, note="X_BEARER_TOKEN is not configured; no community posts or synthetic sentiment are shown."),
    )
    assert result.availability == "unavailable"
    assert result.items == []
    assert "synthetic sentiment" in result.availability_detail


def test_live_posts_stay_unverified_and_outside_hazard_scores():
    post = CommunityPost(
        post_id="123",
        text="Road is closed near the flood.",
        created_at=datetime(2026, 7, 16, 18, tzinfo=timezone.utc),
        language="en",
        tone="concern_language",
        report_type="possible_impact_report",
        tags=["flooding", "road access"],
        source_url="https://x.com/i/web/status/123",
    )
    result = build_community_signals(_event(), AdapterResponse("X API", DataStatus.LIVE, [post]))
    assert result.availability == "available"
    assert result.items[0].verification_status == "unverified"
    assert "outside the hazard score" in result.availability_detail
