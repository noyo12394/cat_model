from datetime import datetime, timedelta, timezone

from app.services.event_fusion import Signal, fuse_signals


def _dt(hours: float) -> datetime:
    return datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc) + timedelta(hours=hours)


def test_nearby_related_signals_fuse_into_one_cluster():
    signals = [
        Signal("s1", "flash_flood", _dt(0), (-75.37, 40.62), watershed="lehigh"),
        Signal("s2", "flood", _dt(1), (-75.372, 40.621), watershed="lehigh"),
        Signal("s3", "severe_weather", _dt(2), (-75.371, 40.619), watershed="lehigh"),
    ]
    clusters = fuse_signals(signals)
    assert len(clusters) == 1
    assert set(clusters[0].signal_ids) == {"s1", "s2", "s3"}
    assert "watershed" in clusters[0].matched_on


def test_far_apart_unrelated_hazard_does_not_fuse():
    signals = [
        Signal("s1", "flash_flood", _dt(0), (-75.37, 40.62), watershed="lehigh"),
        Signal("s2", "earthquake", _dt(0.1), (10.0, 10.0), watershed=None),
    ]
    clusters = fuse_signals(signals)
    assert len(clusters) == 2


def test_same_hazard_far_outside_time_window_does_not_fuse():
    signals = [
        Signal("s1", "flood", _dt(0), (-75.37, 40.62)),
        Signal("s2", "flood", _dt(48), (-75.37, 40.62)),
    ]
    clusters = fuse_signals(signals, time_window_hours=6.0)
    assert len(clusters) == 2


def test_seeded_incident_signals_fuse_under_same_algorithm(repo):
    """Sanity check that the demo dataset's own related_signal_ids would
    plausibly cluster under the general-purpose fusion rule, not just the
    canned FusionReason narrative."""
    incident = repo.get_incident("developing-flood-bethlehem", mode="live")
    alerts = repo.list_alerts(mode="live")
    sensors = [s for s in repo.list_sensors(mode="live") if s.sensor_id == "fac-gauge-lehigh"][-3:]

    signals = [
        Signal(a.alert_id, a.hazard_type.value, a.effective_at, tuple(a.geometry.coordinates[0][0]))
        for a in alerts
    ] + [Signal(s.id, "flood", s.observed_at, tuple(s.geometry.coordinates)) for s in sensors]

    clusters = fuse_signals(signals, time_window_hours=6.0, distance_km=30.0)
    assert len(clusters) == 1
    assert incident is not None
