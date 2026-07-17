from __future__ import annotations

from app.db.memory_repository import MemoryRepository
from app.services.community_pulse import SENTIMENT_WEIGHT, build_community_pulse


def _pulse():
    return build_community_pulse(MemoryRepository())


def test_reports_are_only_user_reported_or_unverified():
    """Community mood must never be presented as observed or official."""
    pulse = _pulse()
    assert pulse.total_reports > 0
    assert all(r.certainty.value in ("user_reported", "unverified") for r in pulse.reports)
    assert pulse.data_status.value == "demo"
    assert pulse.is_demo is True


def test_sentiment_breakdown_counts_reconcile_with_total():
    pulse = _pulse()
    assert sum(b.count for b in pulse.sentiment_breakdown) == pulse.total_reports
    for bucket in pulse.sentiment_breakdown:
        assert 0.0 <= bucket.share <= 1.0


def test_concern_index_is_a_deterministic_weighted_count():
    """The score must be reproducible from the published weights, not an LLM."""
    pulse = _pulse()
    expected = round(
        sum(SENTIMENT_WEIGHT.get(r.sentiment, 0.4) for r in pulse.reports) / pulse.total_reports,
        3,
    )
    assert pulse.concern_index.score == expected
    assert pulse.concern_index.band in {"calm", "watchful", "concerned", "alarmed"}
    assert pulse.concern_index.trend in {"rising", "steady", "easing"}


def test_conflicting_rumors_are_surfaced_not_hidden():
    pulse = _pulse()
    # The seeded set includes unverified rumors that conflict with confirmed conditions.
    assert pulse.corroboration.conflicts > 0
    rumor_reports = [r for r in pulse.reports if r.corroboration == "conflicts"]
    assert all(r.certainty.value == "unverified" for r in rumor_reports)
    total = (
        pulse.corroboration.corroborated
        + pulse.corroboration.uncorroborated
        + pulse.corroboration.conflicts
    )
    assert total == pulse.total_reports


def test_theme_clusters_cover_every_report():
    pulse = _pulse()
    assert sum(c.count for c in pulse.theme_clusters) == pulse.total_reports
    assert pulse.responsible_use  # non-empty responsible-use guidance
    assert pulse.limitations
