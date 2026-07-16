from app.schemas.enums import Confidence
from app.services.confidence import downgrade_for_staleness, score_to_band


def test_score_to_band_boundaries():
    assert score_to_band(0.9) == Confidence.HIGH
    assert score_to_band(0.7) == Confidence.HIGH
    assert score_to_band(0.69) == Confidence.MODERATE
    assert score_to_band(0.4) == Confidence.MODERATE
    assert score_to_band(0.1) == Confidence.LOW


def test_downgrade_for_staleness_none_unaffected():
    assert downgrade_for_staleness(Confidence.HIGH, None) == Confidence.HIGH


def test_downgrade_for_staleness_fresh_unaffected():
    assert downgrade_for_staleness(Confidence.HIGH, 10) == Confidence.HIGH


def test_downgrade_for_staleness_moderately_old_caps_high():
    assert downgrade_for_staleness(Confidence.HIGH, 90) == Confidence.MODERATE
    assert downgrade_for_staleness(Confidence.MODERATE, 90) == Confidence.MODERATE


def test_downgrade_for_staleness_very_old_forces_low():
    assert downgrade_for_staleness(Confidence.HIGH, 500) == Confidence.LOW
