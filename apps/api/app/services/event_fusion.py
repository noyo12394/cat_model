"""Event Fusion AI (section 31.1).

Groups related alerts, forecasts, sensor changes and reports into a single
evolving incident. The matching rule is intentionally simple and
explainable: signals fuse when they agree closely enough on hazard type,
time window and location. This is deliberately NOT a black box - every
grouping decision can be printed as a plain-language reason, which is what
the Incident Room's "why were these grouped together" explanation shows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schemas.enums import Confidence
from app.services.confidence import score_to_band
from app.services.geo import haversine_km

RELATED_HAZARDS = {
    "flood": {"flood", "flash_flood", "severe_weather"},
    "flash_flood": {"flood", "flash_flood", "severe_weather"},
}


@dataclass
class Signal:
    signal_id: str
    hazard_type: str
    observed_at: datetime
    center: tuple[float, float]
    watershed: str | None = None
    source: str | None = None


@dataclass
class FusionCluster:
    signal_ids: list[str]
    matched_on: list[str]
    match_confidence: Confidence
    explanation: str


def _hazards_related(a: str, b: str) -> bool:
    if a == b:
        return True
    return b in RELATED_HAZARDS.get(a, set())


def fuse_signals(
    signals: list[Signal],
    time_window_hours: float = 6.0,
    distance_km: float = 25.0,
) -> list[FusionCluster]:
    """Greedy single-pass clustering. Deterministic and explainable, which
    matters more here than raw clustering optimality at this data scale."""
    clusters: list[list[Signal]] = []

    for signal in sorted(signals, key=lambda s: s.observed_at):
        placed = False
        for cluster in clusters:
            anchor = cluster[0]
            same_time_window = (
                abs((signal.observed_at - anchor.observed_at).total_seconds()) / 3600.0
                <= time_window_hours
            )
            same_place = haversine_km(signal.center, anchor.center) <= distance_km
            same_hazard = _hazards_related(anchor.hazard_type, signal.hazard_type)
            same_watershed = (
                signal.watershed is not None
                and anchor.watershed is not None
                and signal.watershed == anchor.watershed
            )
            if same_hazard and (same_place or same_watershed) and same_time_window:
                cluster.append(signal)
                placed = True
                break
        if not placed:
            clusters.append([signal])

    results: list[FusionCluster] = []
    for cluster in clusters:
        anchor = cluster[0]
        matched_on = ["hazard_type", "time_window"]
        if any(s.watershed and s.watershed == anchor.watershed for s in cluster[1:]):
            matched_on.append("watershed")
        if len(cluster) > 1:
            matched_on.append("geometry")
        score = 0.5 + 0.1 * min(len(cluster) - 1, 5)
        explanation = (
            f"{len(cluster)} signal(s) share hazard type '{anchor.hazard_type}' within "
            f"{time_window_hours:.0f} hours and are co-located, so they were grouped "
            "into one incident."
            if len(cluster) > 1
            else f"Only one signal of hazard type '{anchor.hazard_type}' found; not grouped with others."
        )
        results.append(
            FusionCluster(
                signal_ids=[s.signal_id for s in cluster],
                matched_on=matched_on,
                match_confidence=score_to_band(score),
                explanation=explanation,
            )
        )
    return results
