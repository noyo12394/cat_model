from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.common import GeoPoint, Provenance
from app.schemas.enums import DataStatus, SourceName
from app.schemas.event import SensorObservation


def test_geo_point_requires_two_coordinates():
    with pytest.raises(ValidationError):
        GeoPoint(coordinates=(1.0,))  # type: ignore[arg-type]


def test_sensor_observation_normalizes_required_fields():
    obs = SensorObservation(
        id="s1",
        sensor_id="gauge-1",
        sensor_name="Test Gauge",
        sensor_type="river_gauge",
        geometry=GeoPoint(coordinates=(-75.0, 40.0)),
        observed_at=datetime.now(timezone.utc),
        value=5.2,
        unit="ft",
        provenance=Provenance(
            source=SourceName.USGS_WATER,
            source_organization="USGS",
            retrieved_at=datetime.now(timezone.utc),
            data_status=DataStatus.LIVE,
        ),
    )
    assert obs.value == 5.2
    assert obs.provenance.data_status == DataStatus.LIVE
    assert obs.is_anomalous is False
