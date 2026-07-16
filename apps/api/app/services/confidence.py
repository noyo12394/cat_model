"""Confidence banding helpers.

We deliberately never emit a fake-precision numeric probability to the user
(principle 2.5). Internally we compute a 0-1 score to rank/threshold things,
then immediately collapse it to a Confidence band before it reaches any
response schema.
"""

from __future__ import annotations

from app.schemas.enums import Confidence


def score_to_band(score: float) -> Confidence:
    if score >= 0.7:
        return Confidence.HIGH
    if score >= 0.4:
        return Confidence.MODERATE
    return Confidence.LOW


def downgrade_for_staleness(band: Confidence, staleness_minutes: float | None) -> Confidence:
    """Old data should never look as trustworthy as fresh data."""
    if staleness_minutes is None:
        return band
    if staleness_minutes <= 30:
        return band
    if staleness_minutes <= 180:
        return Confidence.MODERATE if band == Confidence.HIGH else band
    return Confidence.LOW
