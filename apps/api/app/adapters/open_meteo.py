"""Thin adapter for public, already-run weather-model products.

EarthPulse does not train or execute a global model in a Vercel request.  This
adapter asks a public forecast service for the latest available model run and
keeps the returned model identity so the UI can state exactly what it is
showing.  A missing GraphCast product deliberately falls back to a labelled
numerical-weather forecast rather than being presented as ML output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapters.base import AdapterResponse, safe_get_json
from app.schemas.enums import DataStatus

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GFS_URL = "https://api.open-meteo.com/v1/gfs"
SEASONAL_URL = "https://seasonal-api.open-meteo.com/v1/seasonal"
SOURCE_URL = "https://open-meteo.com/en/docs"
SEASONAL_SOURCE_URL = "https://open-meteo.com/en/docs/seasonal-forecast-api"
HOURLY_VARIABLES = "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m,cape"


@dataclass(frozen=True)
class WeatherModelRun:
    model_name: str
    coverage_type: str
    source_url: str
    data: dict[str, Any]
    note: str | None = None


async def fetch_short_range_weather_model(latitude: float, longitude: float) -> AdapterResponse[WeatherModelRun]:
    """Return GraphCast output when the provider has it, else labelled NWP data."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_VARIABLES,
        "forecast_days": 16,
        "timezone": "GMT",
        "models": "gfs_graphcast025",
    }
    graphcast = await safe_get_json(GFS_URL, params)
    if _has_numeric_hourly(graphcast):
        return AdapterResponse(
            source_name="Open-Meteo",
            status=DataStatus.LIVE,
            items=[WeatherModelRun("GraphCast 0.25°", "short_range_ml", SOURCE_URL, graphcast)],
        )

    fallback = await safe_get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": HOURLY_VARIABLES,
            "forecast_days": 16,
            "timezone": "GMT",
        },
    )
    if _has_numeric_hourly(fallback):
        return AdapterResponse(
            source_name="Open-Meteo",
            status=DataStatus.LIVE,
            items=[WeatherModelRun(
                "Best-match numerical weather forecast",
                "short_range_numerical",
                SOURCE_URL,
                fallback,
                "The GraphCast product was not populated for this query, so the latest available numerical forecast is shown and labelled separately.",
            )],
        )
    return AdapterResponse(
        source_name="Open-Meteo",
        status=DataStatus.UNAVAILABLE,
        note="No populated short-range weather-model run was returned for this location.",
    )


async def fetch_seasonal_weather_ensemble(latitude: float, longitude: float) -> AdapterResponse[WeatherModelRun]:
    """Return the public ECMWF seasonal ensemble, limited to its published horizon."""
    data = await safe_get_json(
        SEASONAL_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_mean,precipitation_sum",
            "forecast_days": 210,
            "timezone": "GMT",
        },
    )
    daily = data.get("daily") if isinstance(data, dict) else None
    if isinstance(daily, dict) and isinstance(daily.get("time"), list) and daily.get("time"):
        return AdapterResponse(
            source_name="Open-Meteo",
            status=DataStatus.LIVE,
            items=[WeatherModelRun("ECMWF seasonal ensemble", "seasonal_ensemble", SEASONAL_SOURCE_URL, data)],
        )
    return AdapterResponse(
        source_name="Open-Meteo",
        status=DataStatus.UNAVAILABLE,
        note="No populated seasonal ensemble was returned for this location.",
    )


def _has_numeric_hourly(data: dict[str, Any] | list[Any] | None) -> bool:
    if not isinstance(data, dict) or not isinstance(data.get("hourly"), dict):
        return False
    hourly = data["hourly"]
    for key in ("temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m"):
        values = hourly.get(key)
        if isinstance(values, list) and any(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            return True
    return False
