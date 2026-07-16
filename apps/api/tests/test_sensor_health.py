from datetime import datetime, timezone

from app.schemas.common import GeoPoint, Provenance
from app.schemas.enums import DataStatus, SourceName
from app.schemas.event import SensorObservation
from app.services.sensor_health import check_sensor_health


def test_seeded_live_sensors_are_not_frozen_or_jumpy(repo):
    flags = check_sensor_health(repo, mode="live")
    issues = {f.issue for f in flags}
    assert "frozen" not in issues
    assert "unlikely_jump" not in issues


def _obs(sensor_id: str, value: float, at: datetime) -> SensorObservation:
    return SensorObservation(
        id=f"{sensor_id}-{at.isoformat()}",
        sensor_id=sensor_id,
        sensor_name="Test sensor",
        sensor_type="river_gauge",
        geometry=GeoPoint(coordinates=(-75.0, 40.0)),
        observed_at=at,
        value=value,
        unit="ft",
        provenance=Provenance(
            source=SourceName.USGS_WATER,
            source_organization="test",
            retrieved_at=at,
            data_status=DataStatus.DEMO,
        ),
    )


def test_frozen_sensor_detected_directly(monkeypatch, repo):
    now = datetime.now(timezone.utc)
    frozen_series = [_obs("test-sensor", 5.0, now.replace(microsecond=0)) for _ in range(4)]
    monkeypatch.setattr(repo, "list_sensors", lambda mode="live_demo": frozen_series)
    flags = check_sensor_health(repo, mode="live")
    assert any(f.issue == "frozen" for f in flags)
