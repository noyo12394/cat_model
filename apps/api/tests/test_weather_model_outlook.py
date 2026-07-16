from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import AdapterResponse
from app.adapters.open_meteo import WeatherModelRun
from app.schemas.enums import DataStatus
from app.services.weather_model_outlook import _from_seasonal_ensemble, _from_short_range


def test_short_range_response_reports_drivers_without_inventing_a_hazard():
    now = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    target = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    run = WeatherModelRun(
        model_name="GraphCast 0.25°",
        coverage_type="short_range_ml",
        source_url="https://open-meteo.com/en/docs",
        data={
            "hourly_units": {"temperature_2m": "°C", "precipitation": "mm", "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h"},
            "hourly": {
                "time": ["2026-07-17T00:00", "2026-07-17T12:00", "2026-07-18T00:00"],
                "temperature_2m": [18.0, 23.0, 20.0],
                "precipitation": [1.2, 2.3, 9.0],
                "wind_speed_10m": [12.0, 18.0, 30.0],
                "wind_gusts_10m": [22.0, 34.0, 45.0],
            },
        },
    )
    response = _from_short_range(target, 24, (-75.37, 40.63), "Bethlehem", AdapterResponse("Open-Meteo", DataStatus.LIVE, [run]), now)

    assert response.availability == "available"
    assert response.coverage_type == "short_range_ml"
    assert response.metrics[0].key == "precipitation_24h"
    assert response.metrics[0].value == 3.5
    assert "not a prediction" in response.availability_detail


def test_seasonal_response_keeps_ensemble_spread_and_explicit_limit():
    now = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    target = datetime(2026, 12, 15, 12, tzinfo=timezone.utc)
    daily = {"time": ["2026-12-14", "2026-12-15"]}
    for member, temperature, rain in (("01", 4.0, 0.0), ("02", 5.0, 1.0), ("03", 6.0, 4.0), ("04", 7.0, 7.0), ("05", 8.0, 14.0)):
        daily[f"temperature_2m_mean_member{member}"] = [3.0, temperature]
        daily[f"precipitation_sum_member{member}"] = [0.0, rain]
    run = WeatherModelRun(
        model_name="ECMWF seasonal ensemble",
        coverage_type="seasonal_ensemble",
        source_url="https://open-meteo.com/en/docs/seasonal-forecast-api",
        data={"daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"}, "daily": daily},
    )
    response = _from_seasonal_ensemble(target, 24 * 152, (-75.37, 40.63), "Bethlehem", AdapterResponse("Open-Meteo", DataStatus.LIVE, [run]), now)

    assert response.availability == "available"
    assert response.coverage_type == "seasonal_ensemble"
    assert response.metrics[0].value == 6.0
    assert response.metrics[0].range_low is not None
    assert "not a scheduled event" in response.availability_detail
