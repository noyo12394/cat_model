"""Registry describing every adapter for the Source Health page (section 42)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDescriptor:
    key: str
    display_name: str
    organization: str
    requires_key_env: str | None
    docs_url: str


SOURCE_REGISTRY: list[SourceDescriptor] = [
    SourceDescriptor("NWS", "Weather alerts", "National Weather Service", None,
                      "https://www.weather.gov/documentation/services-web-api"),
    SourceDescriptor("USGS_WATER", "River & stream gauges", "U.S. Geological Survey", None,
                      "https://waterservices.usgs.gov/"),
    SourceDescriptor("USGS_QUAKE", "Earthquakes", "U.S. Geological Survey", None,
                      "https://earthquake.usgs.gov/earthquakes/feed/"),
    SourceDescriptor("NASA_FIRMS", "Active fire detections", "NASA FIRMS", "FIRMS_MAP_KEY",
                      "https://firms.modaps.eosdis.nasa.gov/api/"),
    SourceDescriptor("AIRNOW", "Air quality", "AirNow", "AIRNOW_API_KEY",
                      "https://docs.airnowapi.org/"),
    SourceDescriptor("OPENFEMA", "Historical disaster declarations", "FEMA", None,
                      "https://www.fema.gov/about/openfema/api"),
    SourceDescriptor("GOOGLE_ROUTES", "Route analysis", "Google Maps Platform",
                      "GOOGLE_MAPS_SERVER_API_KEY", "https://developers.google.com/maps/documentation/routes"),
]
