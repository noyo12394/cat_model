"""Sensor Health AI (section 31.5): frozen, jumpy, stale or disagreeing sensors."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from app.db.memory_repository import MemoryRepository

FROZEN_TOLERANCE = 0.01
JUMP_THRESHOLD_STD_MULTIPLIER = 4.0
STALE_MINUTES = 60.0


class SensorHealthFlag(BaseModel):
    sensor_id: str
    sensor_name: str
    issue: str
    detail: str


def check_sensor_health(repo: MemoryRepository, mode: str = "live") -> list[SensorHealthFlag]:
    flags: list[SensorHealthFlag] = []
    obs = repo.list_sensors(mode="replay" if mode == "replay" else "live_demo")
    by_sensor: dict[str, list] = {}
    for o in obs:
        by_sensor.setdefault(o.sensor_id, []).append(o)

    now = datetime.now(timezone.utc)
    for sensor_id, series in by_sensor.items():
        series = sorted(series, key=lambda o: o.observed_at)
        name = series[-1].sensor_name
        latest = series[-1]

        if latest.observed_at.tzinfo is None:
            observed_at = latest.observed_at.replace(tzinfo=timezone.utc)
        else:
            observed_at = latest.observed_at
        staleness_min = (now - observed_at).total_seconds() / 60.0
        if mode == "live" and staleness_min > STALE_MINUTES:
            flags.append(
                SensorHealthFlag(
                    sensor_id=sensor_id,
                    sensor_name=name,
                    issue="stale",
                    detail=f"Last observation is {staleness_min:.0f} minutes old.",
                )
            )

        if len(series) >= 3:
            deltas = [abs(series[i].value - series[i - 1].value) for i in range(1, len(series))]
            avg_delta = sum(deltas) / len(deltas)
            if avg_delta < FROZEN_TOLERANCE:
                flags.append(
                    SensorHealthFlag(
                        sensor_id=sensor_id,
                        sensor_name=name,
                        issue="frozen",
                        detail="Value has not changed across recent observations.",
                    )
                )
            last_delta = deltas[-1]
            if avg_delta > 0 and last_delta > JUMP_THRESHOLD_STD_MULTIPLIER * avg_delta:
                flags.append(
                    SensorHealthFlag(
                        sensor_id=sensor_id,
                        sensor_name=name,
                        issue="unlikely_jump",
                        detail=f"Latest change ({last_delta:.2f}) is much larger than the recent average ({avg_delta:.2f}).",
                    )
                )
    return flags
