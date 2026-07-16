"""Convert public forecast-model output into a cautious, date-specific brief."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import quantiles
from typing import Any

from app.adapters.base import AdapterResponse
from app.adapters.open_meteo import WeatherModelRun, fetch_seasonal_weather_ensemble, fetch_short_range_weather_model
from app.schemas.enums import DataStatus
from app.schemas.weather_model_outlook import ModelWeatherMetric, ModelWeatherOutlookResponse

SHORT_RANGE_HOURS = 16 * 24
SEASONAL_HOURS = 210 * 24


async def build_model_weather_outlook(
    target_at: datetime,
    latitude: float,
    longitude: float,
    location_name: str,
    *,
    now: datetime | None = None,
) -> ModelWeatherOutlookResponse:
    """Provide weather drivers only within a source's published time range."""
    now = now or datetime.now(timezone.utc)
    target_at = _utc(target_at)
    horizon_hours = (target_at - now).total_seconds() / 3600
    center = (round(longitude, 5), round(latitude, 5))

    if horizon_hours <= 0:
        return _unavailable(target_at, horizon_hours, center, location_name, now, "Choose a future UTC date. Use the live view for observations.")
    if horizon_hours <= SHORT_RANGE_HOURS:
        response = await fetch_short_range_weather_model(latitude, longitude)
        return _from_short_range(target_at, horizon_hours, center, location_name, response, now)
    if horizon_hours <= SEASONAL_HOURS:
        response = await fetch_seasonal_weather_ensemble(latitude, longitude)
        return _from_seasonal_ensemble(target_at, horizon_hours, center, location_name, response, now)
    return _unavailable(
        target_at,
        horizon_hours,
        center,
        location_name,
        now,
        "No supported forecast product reaches this date. EarthPulse will not fabricate a weather outlook outside the published 16-day model or seven-month seasonal-ensemble horizons.",
    )


def _from_short_range(
    target_at: datetime,
    horizon_hours: float,
    center: tuple[float, float],
    location_name: str,
    response: AdapterResponse[WeatherModelRun],
    now: datetime,
) -> ModelWeatherOutlookResponse:
    if response.status == DataStatus.UNAVAILABLE or not response.items:
        return _unavailable(target_at, horizon_hours, center, location_name, now, response.note or "The short-range weather-model source is unavailable.")
    run = response.items[0]
    hourly = run.data.get("hourly") if isinstance(run.data, dict) else None
    units = run.data.get("hourly_units") if isinstance(run.data, dict) else None
    if not isinstance(hourly, dict) or not isinstance(units, dict):
        return _unavailable(target_at, horizon_hours, center, location_name, now, "The weather-model response did not contain usable hourly fields.")

    indices = _day_indices(hourly.get("time"), target_at.date())
    if not indices:
        return _unavailable(target_at, horizon_hours, center, location_name, now, "The selected date is outside the returned weather-model run.")
    metrics = _short_metrics(hourly, units, indices)
    if not metrics:
        return _unavailable(target_at, horizon_hours, center, location_name, now, "The weather-model run did not contain populated atmospheric variables for this date.")

    is_ml = run.coverage_type == "short_range_ml"
    detail = (
        f"Direct atmospheric drivers for {location_name} on {target_at:%d %b %Y} UTC from the latest available model run. "
        "These values are not a prediction that a flood, wildfire, or other disaster will occur."
    )
    if run.note:
        detail = f"{detail} {run.note}"
    return ModelWeatherOutlookResponse(
        target_at=target_at,
        horizon_hours=round(horizon_hours, 1),
        availability="available",
        availability_label="ML weather-model guidance" if is_ml else "Numerical weather-model guidance",
        availability_detail=detail,
        coverage_type=run.coverage_type,  # type: ignore[arg-type]
        location_name=location_name,
        center=center,
        model_name=run.model_name,
        source_url=run.source_url,
        generated_at=now,
        data_status=response.status,
        metrics=metrics,
        reliability_note="Useful for short-range atmospheric conditions at this point. It is not an impact forecast and must be checked against local warnings and observations.",
        limitations=[
            "A point weather model cannot determine a flood footprint, road closure, building impact, or evacuation need.",
            "EarthPulse does not use this output to predict new earthquakes, wildfires, landslides, or named disaster events.",
        ],
    )


def _from_seasonal_ensemble(
    target_at: datetime,
    horizon_hours: float,
    center: tuple[float, float],
    location_name: str,
    response: AdapterResponse[WeatherModelRun],
    now: datetime,
) -> ModelWeatherOutlookResponse:
    if response.status == DataStatus.UNAVAILABLE or not response.items:
        return _unavailable(target_at, horizon_hours, center, location_name, now, response.note or "The seasonal ensemble source is unavailable.")
    run = response.items[0]
    daily = run.data.get("daily") if isinstance(run.data, dict) else None
    units = run.data.get("daily_units") if isinstance(run.data, dict) else None
    if not isinstance(daily, dict) or not isinstance(units, dict):
        return _unavailable(target_at, horizon_hours, center, location_name, now, "The seasonal ensemble response did not contain usable daily fields.")
    target_index = _date_index(daily.get("time"), target_at.date())
    if target_index is None:
        return _unavailable(target_at, horizon_hours, center, location_name, now, "The selected date is outside the returned seasonal ensemble period.")
    metrics = _seasonal_metrics(daily, units, target_index)
    if not metrics:
        return _unavailable(target_at, horizon_hours, center, location_name, now, "The seasonal ensemble did not contain populated values for this date.")
    return ModelWeatherOutlookResponse(
        target_at=target_at,
        horizon_hours=round(horizon_hours, 1),
        availability="available",
        availability_label="Seasonal ensemble signal",
        availability_detail=(
            f"ECMWF ensemble conditions near {location_name} for {target_at:%d %b %Y} UTC. "
            "This is broad seasonal guidance, not a scheduled event or a day-specific hazard prediction."
        ),
        coverage_type="seasonal_ensemble",
        location_name=location_name,
        center=center,
        model_name=run.model_name,
        source_url=run.source_url,
        generated_at=now,
        data_status=response.status,
        metrics=metrics,
        reliability_note="Use the ensemble spread to understand uncertainty. Treat this as regional climate guidance, not local operational forecasting.",
        limitations=[
            "Seasonal ensembles are not bias-corrected local hazard forecasts and cannot schedule individual storms, floods, fires, earthquakes, or outages.",
            "Wider ensemble ranges indicate more model disagreement; they are not a probability that an event will happen.",
        ],
    )


def _short_metrics(hourly: dict[str, Any], units: dict[str, Any], indices: list[int]) -> list[ModelWeatherMetric]:
    metrics: list[ModelWeatherMetric] = []
    precipitation = _values_at(hourly.get("precipitation"), indices)
    if precipitation:
        metrics.append(ModelWeatherMetric(key="precipitation_24h", label="24 h precipitation", value=round(sum(precipitation), 1), unit=str(units.get("precipitation", "mm")), detail="Sum of available hourly values on the selected UTC date."))
    wind_gusts = _values_at(hourly.get("wind_gusts_10m"), indices)
    if wind_gusts:
        metrics.append(ModelWeatherMetric(key="wind_gusts_10m", label="Peak wind gust", value=round(max(wind_gusts), 1), unit=str(units.get("wind_gusts_10m", "km/h")), detail="Highest available hourly value on the selected UTC date."))
    wind = _values_at(hourly.get("wind_speed_10m"), indices)
    if wind:
        metrics.append(ModelWeatherMetric(key="wind_speed_10m", label="Peak sustained wind", value=round(max(wind), 1), unit=str(units.get("wind_speed_10m", "km/h")), detail="Highest available hourly value on the selected UTC date."))
    temperature = _values_at(hourly.get("temperature_2m"), indices)
    if temperature:
        metrics.append(ModelWeatherMetric(key="temperature_2m", label="Temperature range", value=round(sum(temperature) / len(temperature), 1), unit=str(units.get("temperature_2m", "°C")), range_low=round(min(temperature), 1), range_high=round(max(temperature), 1), detail="Mean with low–high range across available hourly values."))
    return metrics


def _seasonal_metrics(daily: dict[str, Any], units: dict[str, Any], index: int) -> list[ModelWeatherMetric]:
    metrics: list[ModelWeatherMetric] = []
    for key, label in (("temperature_2m_mean", "Ensemble mean temperature"), ("precipitation_sum", "Ensemble mean precipitation")):
        values = _ensemble_values(daily, key, index)
        if not values:
            continue
        lower, upper = _spread(values)
        metrics.append(ModelWeatherMetric(
            key=key,
            label=label,
            value=round(sum(values) / len(values), 1),
            unit=str(units.get(key, "°C" if key.startswith("temperature") else "mm")),
            range_low=round(lower, 1),
            range_high=round(upper, 1),
            detail=f"Central 80% range across {len(values)} available ensemble members.",
        ))
    return metrics


def _day_indices(times: Any, target_date: datetime.date) -> list[int]:
    if not isinstance(times, list):
        return []
    return [index for index, value in enumerate(times) if isinstance(value, str) and value[:10] == target_date.isoformat()]


def _date_index(times: Any, target_date: datetime.date) -> int | None:
    if not isinstance(times, list):
        return None
    try:
        return times.index(target_date.isoformat())
    except ValueError:
        return None


def _values_at(values: Any, indices: list[int]) -> list[float]:
    if not isinstance(values, list):
        return []
    return [float(values[index]) for index in indices if index < len(values) and isinstance(values[index], (int, float)) and not isinstance(values[index], bool)]


def _ensemble_values(daily: dict[str, Any], key: str, index: int) -> list[float]:
    values: list[float] = []
    for member_key, member_series in daily.items():
        if not member_key.startswith(f"{key}_member") or not isinstance(member_series, list) or index >= len(member_series):
            continue
        value = member_series[index]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    if values:
        return values
    series = daily.get(key)
    if isinstance(series, list) and index < len(series) and isinstance(series[index], (int, float)):
        return [float(series[index])]
    return []


def _spread(values: list[float]) -> tuple[float, float]:
    if len(values) < 4:
        return min(values), max(values)
    cuts = quantiles(values, n=10, method="inclusive")
    return cuts[0], cuts[8]


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _unavailable(
    target_at: datetime,
    horizon_hours: float,
    center: tuple[float, float],
    location_name: str,
    now: datetime,
    detail: str,
) -> ModelWeatherOutlookResponse:
    return ModelWeatherOutlookResponse(
        target_at=target_at,
        horizon_hours=round(horizon_hours, 1),
        availability="unavailable",
        availability_label="Model guidance unavailable",
        availability_detail=detail,
        coverage_type="unavailable",
        location_name=location_name,
        center=center,
        generated_at=now,
        data_status=DataStatus.UNAVAILABLE,
        reliability_note="No model-derived conditions are shown when the requested date is outside a published source horizon.",
        limitations=["EarthPulse does not extrapolate a weather model beyond its published coverage."],
    )
