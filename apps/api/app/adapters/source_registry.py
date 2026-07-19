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
    access_method: str = "HTTP API"
    license_summary: str = "Terms require source-specific review"
    commercial_use_status: str = "review_required"
    update_frequency: str = "Provider controlled"
    geographic_coverage: str = "Source dependent"
    spatial_resolution: str = "Source dependent"
    temporal_resolution: str = "Source dependent"
    required_attribution: str = "See provider terms"
    quality_notes: str = "Availability and fitness must be checked at run time."
    deprecation_status: str = "active"
    fallback_source: str | None = None
    terms_url: str | None = None
    verified_at: str = "2026-07-18"


SOURCE_REGISTRY: list[SourceDescriptor] = [
    SourceDescriptor(
        "NOMINATIM", "Submitted place search", "OpenStreetMap Nominatim", None,
        "https://nominatim.org/release-docs/latest/api/Search/",
        license_summary="OpenStreetMap data under ODbL; public Nominatim usage policy applies",
        commercial_use_status="prototype_low_volume_only",
        update_frequency="Provider controlled; requested only on explicit submit",
        geographic_coverage="Global OpenStreetMap coverage",
        spatial_resolution="Matched OSM feature or address point",
        temporal_resolution="Current provider index",
        required_attribution="© OpenStreetMap contributors",
        quality_notes="A geocoded position is not a hazard observation, exposure record, or risk result.",
        fallback_source="No guessed location; return no results",
        terms_url="https://operations.osmfoundation.org/policies/nominatim/",
    ),
    SourceDescriptor(
        "GDACS", "Global multi-hazard events", "UN–European Commission GDACS", None,
        "https://www.gdacs.org/gdacsapi/swagger/index.html",
        license_summary="GDACS terms-controlled indicative information supplied as-is",
        commercial_use_status="review_required",
        update_frequency="Near real time; provider controlled",
        geographic_coverage="Global",
        spatial_resolution="Event location or provider footprint",
        temporal_resolution="Event dependent",
        required_attribution="Identify GDACS and retain links to official reports",
        quality_notes="Not a substitute for authoritative national or local warnings.",
        fallback_source="No silent fallback; return unavailable",
        terms_url="https://www.gdacs.org/About/termofuse.aspx",
    ),
    SourceDescriptor(
        "NWS", "Weather alerts", "National Weather Service", None,
        "https://www.weather.gov/documentation/services-web-api",
        license_summary="Open U.S. Government data; endpoint documented as free for any purpose",
        commercial_use_status="permitted_with_source_review",
        update_frequency="Alert issuance dependent",
        geographic_coverage="United States and covered territories",
        spatial_resolution="Alert polygon or forecast zone",
        temporal_resolution="Alert effective and expiry windows",
        required_attribution="Credit the National Weather Service and preserve alert identifiers",
        quality_notes="Client must provide an identifying User-Agent and respect rate limits.",
        fallback_source="Labelled Bethlehem demonstration alerts",
        terms_url="https://www.weather.gov/documentation/services-web-api",
    ),
    SourceDescriptor(
        "USGS_WATER", "River & stream gauges", "U.S. Geological Survey", None,
        "https://api.waterdata.usgs.gov/docs/ogcapi/",
        license_summary="Generally public-domain U.S. Government data; third-party content may differ",
        commercial_use_status="permitted_with_source_review",
        update_frequency="Continuous observations; latest endpoint queried on demand",
        geographic_coverage="United States",
        spatial_resolution="Monitoring station",
        temporal_resolution="Observation dependent",
        required_attribution="Credit the U.S. Geological Survey and preserve station metadata",
        quality_notes="Latest values may be provisional; approval status is preserved in quality flags.",
        fallback_source="Labelled Bethlehem demonstration gauges",
        terms_url="https://www.usgs.gov/data-management/data-licensing",
    ),
    SourceDescriptor(
        "USGS_QUAKE", "Earthquakes", "U.S. Geological Survey", None,
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
        license_summary="Generally public-domain U.S. Government data; third-party content may differ",
        commercial_use_status="permitted_with_source_review",
        update_frequency="Feed window and event updates",
        geographic_coverage="Global earthquake detections",
        spatial_resolution="Event hypocentre and provider products",
        temporal_resolution="Event dependent",
        required_attribution="Credit the U.S. Geological Survey and preserve event links",
        quality_notes="Magnitude, location and review status may be revised after publication.",
        fallback_source="No fabricated earthquake feed; return unavailable",
        terms_url="https://www.usgs.gov/data-management/data-licensing",
    ),
    SourceDescriptor(
        "NASA_FIRMS", "Active fire detections", "NASA FIRMS", "FIRMS_MAP_KEY",
        "https://firms.modaps.eosdis.nasa.gov/api/",
        license_summary="NASA Earthdata/FIRMS product-specific citation and terms apply",
        commercial_use_status="review_required",
        update_frequency="Satellite overpass and product dependent",
        geographic_coverage="Global",
        spatial_resolution="Sensor/product dependent hotspot pixels",
        temporal_resolution="Satellite overpass dependent",
        required_attribution="Use the required FIRMS product citation and sensor attribution",
        quality_notes="A hotspot detection is not an exact fire perimeter.",
        fallback_source="No synthetic fire detections; return unavailable",
        terms_url="https://firms.modaps.eosdis.nasa.gov/content/academy/data_academy.html",
    ),
    SourceDescriptor(
        "AIRNOW", "Air quality", "AirNow", "AIRNOW_API_KEY",
        "https://docs.airnowapi.org/",
        license_summary="AirNow data-use guidelines and reporting-agency attribution apply",
        commercial_use_status="review_required",
        update_frequency="Observation and forecast product dependent",
        geographic_coverage="United States and participating reporting areas",
        spatial_resolution="Monitor or reporting area",
        temporal_resolution="Product dependent",
        required_attribution="Credit AirNow and the reporting agencies",
        quality_notes="Real-time data are preliminary and are not regulatory determinations.",
        fallback_source="Labelled moderate-AQI demonstration only",
        terms_url="https://docs.airnowapi.org/docs/DataUseGuidelines.pdf",
    ),
    SourceDescriptor(
        "OPENFEMA", "Historical disaster declarations", "FEMA", None,
        "https://www.fema.gov/about/openfema/api",
        license_summary="OpenFEMA terms and dataset-specific metadata apply",
        commercial_use_status="review_required",
        update_frequency="Dataset dependent",
        geographic_coverage="United States",
        spatial_resolution="Dataset dependent administrative geography",
        temporal_resolution="Dataset dependent",
        required_attribution="Identify FEMA/OpenFEMA and the exact dataset/version",
        quality_notes="Historical records may be revised, incomplete, or reported at broad geography.",
        fallback_source="No invented declarations; return unavailable",
        terms_url="https://www.fema.gov/about/reports-and-data/openfema/terms-conditions",
    ),
    SourceDescriptor(
        "X_COMMUNITY", "Community reports", "X API", "X_BEARER_TOKEN",
        "https://docs.x.com/x-api/posts/search-recent-posts",
        license_summary="Licensed and restricted by the X Developer Agreement and Policy",
        commercial_use_status="licensed_restricted",
        update_frequency="Query time and plan dependent",
        geographic_coverage="Public posts returned by the approved query",
        spatial_resolution="Only explicit or cautiously extracted location",
        temporal_resolution="Post timestamp",
        required_attribution="Follow X display, attribution, deletion and content requirements",
        quality_notes="Public posts are unverified signals, never physical hazard measurements.",
        fallback_source="None; disabled without an approved token",
        terms_url="https://docs.x.com/developer-terms/agreement",
    ),
    SourceDescriptor(
        "GOOGLE_ROUTES", "Route analysis", "Google Maps Platform",
        "GOOGLE_MAPS_SERVER_API_KEY", "https://developers.google.com/maps/documentation/routes",
        license_summary="Commercial Google Maps Platform service terms and policies apply",
        commercial_use_status="licensed_restricted",
        update_frequency="Request time",
        geographic_coverage="Provider coverage dependent",
        spatial_resolution="Route geometry and legs",
        temporal_resolution="Request and traffic-model dependent",
        required_attribution="Display required Google Maps attribution and third-party notices",
        quality_notes="Caching, display and use with maps are restricted by provider policy.",
        fallback_source="Straight-line distance labelled as such; never presented as a route",
        terms_url="https://developers.google.com/maps/documentation/routes/policies",
    ),
]
