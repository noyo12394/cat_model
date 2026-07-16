"""Deterministic, inspectable global event watch-priority calculation."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.global_event import GlobalEvent
from app.schemas.global_outlook import GlobalWatchItem


def horizon_label(minutes: int) -> str:
    if minutes == 0:
        return "Current operating picture"
    if minutes < 60:
        return f"Next {minutes} minutes"
    if minutes % 60 == 0:
        return f"Next {minutes // 60} hour{'s' if minutes > 60 else ''}"
    return f"Next {minutes // 60}h {minutes % 60}m"


def next_action(minutes: int) -> str:
    if minutes <= 15:
        return "Verify the official report and any national-authority update now."
    if minutes <= 60:
        return "Watch for an official source update or alert-level change."
    if minutes <= 360:
        return "Review exposure and coordination implications if the alert persists."
    return "Reassess at the next source refresh; no event outcome is projected."


def priority_for(event: GlobalEvent, minutes: int, *, now: datetime | None = None) -> GlobalWatchItem:
    """Rank operational attention—not likelihood or physical severity forecast.

    The intentionally small formula is shown in the UI and API documentation:
    alert level (15/45/70) + published GDACS score (0..15, capped) + freshness
    (0..15) + short-window verification emphasis (0..5, red/orange only).
    """
    now = now or datetime.now(timezone.utc)
    level_points = {"red": 70, "orange": 45, "green": 15}.get(event.alert_level, 10)
    score_points = min(15, max(0, round((event.alert_score or 0) * 5)))
    age_hours = max(0, (now - event.modified_at).total_seconds() / 3600)
    freshness_points = 15 if age_hours <= 1 else 12 if age_hours <= 6 else 6 if age_hours <= 24 else 0
    short_window_points = 5 if minutes <= 60 and event.alert_level in {"red", "orange"} else 0
    score = min(100, level_points + score_points + freshness_points + short_window_points)

    if score >= 80:
        label = "Immediate verification"
    elif score >= 55:
        label = "Active watch"
    else:
        label = "Monitor"

    drivers = [f"GDACS {event.alert_level} alert"]
    if event.alert_score is not None:
        drivers.append(f"Published GDACS score {event.alert_score:g}")
    if age_hours <= 1:
        drivers.append("Modified within the last hour")
    elif age_hours <= 6:
        drivers.append("Modified within the last 6 hours")
    else:
        drivers.append("No very recent source modification")

    return GlobalWatchItem(
        event_id=event.event_id,
        name=event.name,
        event_type=event.event_type,
        country=event.country,
        center=event.center,
        alert_level=event.alert_level,
        alert_score=event.alert_score,
        modified_at=event.modified_at,
        priority_score=score,
        priority_label=label,
        drivers=drivers,
        next_action=next_action(minutes),
        report_url=event.report_url,
    )
