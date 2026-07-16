"""What Changed? (section 10).

Reconstructs the incident state as of a comparison time and diffs it against
now: which timeline entries are new, and how much each gauge moved. This
reads directly off the same seeded sensor series and timeline used
elsewhere, so the numbers here are guaranteed consistent with the Location
Capsule / Incident Room / Evidence Trail views.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.db.memory_repository import MemoryRepository
from app.schemas.incident import WhatChanged, WhatChangedItem

COMPARISON_PRESETS_MINUTES = {
    "30_minutes": 30,
    "1_hour": 60,
    "6_hours": 360,
    "yesterday": 24 * 60,
}


def _closest_reading(series: list, at: datetime):
    if not series:
        return None
    return min(series, key=lambda o: abs((o.observed_at - at).total_seconds()))


def compute_what_changed(
    repo: MemoryRepository, incident_id: str, mode: str, compared_to_label: str
) -> WhatChanged | None:
    incident = repo.get_incident(incident_id, mode=mode)
    if not incident:
        return None

    minutes = COMPARISON_PRESETS_MINUTES.get(compared_to_label, 60)
    now_at = incident.updated_at
    compared_to_at = now_at - timedelta(minutes=minutes)

    changes: list[WhatChangedItem] = []

    for sensor_id in ("fac-gauge-monocacy", "fac-gauge-lehigh"):
        series = repo.sensor_series(sensor_id, mode="replay" if mode == "replay" else "live_demo")
        before = _closest_reading(series, compared_to_at)
        after = _closest_reading(series, now_at)
        if before and after and before.observed_at != after.observed_at:
            delta = round(after.value - before.value, 2)
            direction = "increased" if delta > 0 else "decreased" if delta < 0 else "held steady"
            changes.append(
                WhatChangedItem(
                    label=f"{after.sensor_name} {direction}",
                    detail=f"{after.sensor_name} {direction} by {abs(delta)} {after.unit} since {compared_to_label.replace('_', ' ')}.",
                    certainty_class="observed",
                    magnitude=delta,
                    unit=after.unit,
                )
            )

    new_entries = [e for e in incident.timeline if compared_to_at < e.at <= now_at]
    for entry in new_entries:
        changes.append(
            WhatChangedItem(
                label=entry.label,
                detail=entry.detail,
                certainty_class=entry.certainty_class,
            )
        )

    if not any(e.label == "Flash Flood Warning issued" for e in new_entries):
        changes.append(
            WhatChangedItem(
                label="No new official closure has been confirmed",
                detail="No confirmed infrastructure closure since the comparison time.",
                certainty_class="observed",
            )
        )

    return WhatChanged(
        incident_id=incident_id,
        compared_to_label=compared_to_label,
        compared_to_at=compared_to_at,
        now_at=now_at,
        changes=changes,
    )
