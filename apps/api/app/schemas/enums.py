"""Shared enumerations for the EarthPulse common data model.

These enums are the backbone of "show facts, forecasts and AI inferences
differently" (product principle 2.2). Every record in the system carries a
``certainty_class`` so the frontend can render it with the correct evidence
style and never confuse an AI inference with an official warning.
"""

from __future__ import annotations

from enum import Enum


class CertaintyClass(str, Enum):
    """How a piece of information came to exist. Drives evidence styling."""

    OBSERVED = "observed"
    OFFICIAL_ALERT = "official_alert"
    FORECAST = "forecast"
    AI_INFERRED = "ai_inferred"
    USER_REPORTED = "user_reported"
    UNVERIFIED = "unverified"
    HISTORICAL = "historical"
    SIMULATED = "simulated"


class Severity(str, Enum):
    """Status-color severity ladder (section 37). Never the sole indicator."""

    UNKNOWN = "unknown"
    NORMAL = "normal"
    WATCH = "watch"
    ELEVATED = "elevated"
    SEVERE = "severe"
    EXTREME = "extreme"


class Confidence(str, Enum):
    """Coarse, human-legible confidence. We deliberately avoid fake precision
    like "83.42%" (principle 2.5) - confidence is always one of these bands,
    with the numeric basis (if any) available in the evidence trail."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Urgency(str, Enum):
    IMMEDIATE = "immediate"
    EXPECTED = "expected"
    FUTURE = "future"
    PAST = "past"
    UNKNOWN = "unknown"


class HazardType(str, Enum):
    FLOOD = "flood"
    FLASH_FLOOD = "flash_flood"
    SEVERE_WEATHER = "severe_weather"
    EARTHQUAKE = "earthquake"
    WILDFIRE = "wildfire"
    SMOKE = "smoke"
    AIR_QUALITY = "air_quality"
    HURRICANE = "hurricane"
    STORM_SURGE = "storm_surge"
    EXTREME_HEAT = "extreme_heat"
    WINTER_STORM = "winter_storm"
    LANDSLIDE = "landslide"
    TSUNAMI = "tsunami"
    DROUGHT = "drought"


class DataStatus(str, Enum):
    """Freshness/availability state for any source-backed value (principle 2.7)."""

    LIVE = "live"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    DEMO = "demo"


class FacilityType(str, Enum):
    HOSPITAL = "hospital"
    FIRE_STATION = "fire_station"
    SCHOOL = "school"
    BRIDGE = "bridge"
    RIVER_CROSSING = "river_crossing"
    SHELTER = "shelter"
    UTILITY_SUBSTATION = "utility_substation"
    WATER_TREATMENT = "water_treatment"
    ROAD_SEGMENT = "road_segment"
    GAUGE = "gauge"


class OperationalState(str, Enum):
    NORMAL = "normal"
    STRESSED = "stressed"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class SourceName(str, Enum):
    NWS = "NWS"
    USGS_WATER = "USGS_WATER"
    USGS_QUAKE = "USGS_QUAKE"
    NASA_FIRMS = "NASA_FIRMS"
    AIRNOW = "AIRNOW"
    OPENFEMA = "OPENFEMA"
    OSM = "OSM"
    GOOGLE_PLACES = "GOOGLE_PLACES"
    GOOGLE_ROUTES = "GOOGLE_ROUTES"
    EARTHPULSE_FUSION = "EARTHPULSE_FUSION_AI"
    EARTHPULSE_NOWCAST = "EARTHPULSE_IMPACT_NOWCASTING_AI"
    EARTHPULSE_CASCADE = "EARTHPULSE_CASCADE_MODEL"
    EARTHPULSE_ANALOG = "EARTHPULSE_HISTORICAL_ANALOG_AI"
    USER = "USER"
    DEMO_ARCHIVE = "DEMO_ARCHIVE"
