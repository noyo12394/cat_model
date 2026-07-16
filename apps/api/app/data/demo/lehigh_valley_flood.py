"""Seeded demonstration scenario: a developing flood around Bethlehem, PA.

Important honesty note: this dataset uses REAL place names and REAL
approximate geography (Lehigh University, Bethlehem's Lehigh River and
Monocacy Creek, the Hill-to-Hill and Fahy bridges, St. Luke's University
Hospital) because the product needs to demonstrate against recognizable,
real-world places. The specific EVENT - the timeline, gauge readings, and
alert - is a SYNTHETIC composite built for demonstration only. It is not a
transcription of any single real historical flood. Every record produced
from this module is labeled ``is_demo=True`` / ``data_status: demo`` (or
``historical`` in replay mode) so the frontend can never present it as a
live, current, or verified-historical condition (section 46 / 50).

Facility coordinates are approximate, for demonstration purposes, and were
not sourced from a surveyed GIS dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from app.schemas.common import GeoPoint, GeoPolygon, ModelBasis, Provenance
from app.schemas.enums import (
    CertaintyClass,
    Confidence,
    DataStatus,
    FacilityType,
    HazardType,
    OperationalState,
    Severity,
    SourceName,
    Urgency,
)
from app.schemas.event import Alert, Forecast, HazardEvent, SensorObservation
from app.schemas.facility import Facility, InfrastructureDependency
from app.schemas.incident import FusionReason, IncidentDetail, TimelineEntry
from app.schemas.inference import HistoricalAnalog

# --- Real, public place coordinates used as demonstration fixtures ---------

LEHIGH_UNIVERSITY = (-75.3785, 40.6084)
BETHLEHEM_CENTER = (-75.3705, 40.6259)
ALLENTOWN_CENTER = (-75.4714, 40.6023)
EASTON_CENTER = (-75.2213, 40.6884)
PHILADELPHIA_CENTER = (-75.1652, 39.9526)
NYC_CENTER = (-74.0060, 40.7128)

ST_LUKES_BETHLEHEM = (-75.3599, 40.6294)
LVH_MUHLENBERG = (-75.4460, 40.6417)
HILL_TO_HILL_BRIDGE = (-75.3746, 40.6220)
FAHY_BRIDGE = (-75.3660, 40.6180)
BETHLEHEM_FIRE_STATION_1 = (-75.3715, 40.6247)


def _anchor_now() -> datetime:
    return datetime.now(timezone.utc)


@lru_cache
def live_demo_anchor() -> datetime:
    """Frozen at process start so 'updated N minutes ago' stays coherent for a
    session and slowly (honestly) drifts toward stale the longer the process
    has been running - itself a small demonstration of principle 2.7."""
    return _anchor_now()


REPLAY_ANCHOR = datetime(2024, 7, 11, 18, 0, tzinfo=timezone.utc)


def _prov(
    source: SourceName,
    org: str,
    observed_at: datetime,
    retrieved_at: datetime,
    status: DataStatus,
    url: str | None = None,
) -> Provenance:
    return Provenance(
        source=source,
        source_organization=org,
        source_url=url,
        license="Public domain (U.S. Government) / demonstration fixture",
        observed_at=observed_at,
        updated_at=observed_at,
        retrieved_at=retrieved_at,
        data_status=status,
    )


@dataclass
class FloodScenario:
    mode: str  # "live_demo" | "replay"
    anchor: datetime
    facilities: list[Facility] = field(default_factory=list)
    sensors: list[SensorObservation] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    forecasts: list[Forecast] = field(default_factory=list)
    events: list[HazardEvent] = field(default_factory=list)
    incident: IncidentDetail | None = None
    dependencies: list[InfrastructureDependency] = field(default_factory=list)
    analogs: list[HistoricalAnalog] = field(default_factory=list)


def build_flood_scenario(mode: str = "live_demo") -> FloodScenario:
    anchor = live_demo_anchor() if mode == "live_demo" else REPLAY_ANCHOR
    retrieved_at = _anchor_now() if mode == "live_demo" else anchor + timedelta(minutes=5)
    status = DataStatus.DEMO if mode == "live_demo" else DataStatus.DEMO

    def t(minutes_offset: int) -> datetime:
        return anchor + timedelta(minutes=minutes_offset)

    scenario = FloodScenario(mode=mode, anchor=anchor)

    # --- Facilities -----------------------------------------------------
    scenario.facilities = [
        Facility(
            id="fac-stlukes-bethlehem",
            facility_id="fac-stlukes-bethlehem",
            facility_type=FacilityType.HOSPITAL,
            name="St. Luke's University Hospital - Bethlehem Campus",
            geometry=GeoPoint(coordinates=ST_LUKES_BETHLEHEM),
            operational_state=OperationalState.NORMAL,
            attributes={"beds_approx": 480, "trauma_center": True},
            data_completeness=0.8,
            backup_power=True,
            served_population=250_000,
            provenance=_prov(
                SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="fac-lvh-muhlenberg",
            facility_id="fac-lvh-muhlenberg",
            facility_type=FacilityType.HOSPITAL,
            name="Lehigh Valley Hospital - Muhlenberg",
            geometry=GeoPoint(coordinates=LVH_MUHLENBERG),
            operational_state=OperationalState.NORMAL,
            attributes={"beds_approx": 320, "trauma_center": False},
            data_completeness=0.6,
            backup_power=None,
            served_population=180_000,
            provenance=_prov(
                SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="fac-hill-to-hill-bridge",
            facility_id="fac-hill-to-hill-bridge",
            facility_type=FacilityType.BRIDGE,
            name="Hill-to-Hill Bridge",
            geometry=GeoPoint(coordinates=HILL_TO_HILL_BRIDGE),
            operational_state=OperationalState.STRESSED,
            attributes={
                "road_carried": "PA-378",
                "waterway_crossed": "Lehigh River",
                "elevation_note": "estimated, low-lying approach ramps",
            },
            data_completeness=0.5,
            provenance=_prov(
                SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="fac-fahy-bridge",
            facility_id="fac-fahy-bridge",
            facility_type=FacilityType.BRIDGE,
            name="Fahy Bridge",
            geometry=GeoPoint(coordinates=FAHY_BRIDGE),
            operational_state=OperationalState.NORMAL,
            attributes={
                "road_carried": "Water St / Brodhead Rd",
                "waterway_crossed": "Lehigh River",
                "elevation_note": "estimated, higher approach than Hill-to-Hill",
            },
            data_completeness=0.5,
            provenance=_prov(
                SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="fac-bethlehem-fire-1",
            facility_id="fac-bethlehem-fire-1",
            facility_type=FacilityType.FIRE_STATION,
            name="Bethlehem Fire Department - Station 1 (approx.)",
            geometry=GeoPoint(coordinates=BETHLEHEM_FIRE_STATION_1),
            operational_state=OperationalState.NORMAL,
            data_completeness=0.4,
            provenance=_prov(
                SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="fac-gauge-monocacy",
            facility_id="fac-gauge-monocacy",
            facility_type=FacilityType.GAUGE,
            name="Monocacy Creek near Bethlehem (demo gauge)",
            geometry=GeoPoint(coordinates=(-75.3780, 40.6280)),
            operational_state=OperationalState.NORMAL,
            data_completeness=0.9,
            provenance=_prov(
                SourceName.USGS_WATER, "USGS Water Data (demo)", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="fac-gauge-lehigh",
            facility_id="fac-gauge-lehigh",
            facility_type=FacilityType.GAUGE,
            name="Lehigh River at Bethlehem (demo gauge)",
            geometry=GeoPoint(coordinates=(-75.3730, 40.6230)),
            operational_state=OperationalState.NORMAL,
            data_completeness=0.9,
            provenance=_prov(
                SourceName.USGS_WATER, "USGS Water Data (demo)", anchor, retrieved_at, status
            ),
        ),
        Facility(
            id="place-lehigh-university",
            facility_id="place-lehigh-university",
            facility_type=FacilityType.SCHOOL,
            name="Lehigh University",
            geometry=GeoPoint(coordinates=LEHIGH_UNIVERSITY),
            operational_state=OperationalState.NORMAL,
            data_completeness=0.9,
            served_population=7000,
            provenance=_prov(
                SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status
            ),
        ),
    ]

    # --- Sensor observations: two rising gauges --------------------------
    monocacy_series = [
        (-180, 2.1, 0.0),
        (-150, 2.3, 0.4),
        (-120, 2.7, 0.8),
        (-90, 3.4, 1.4),
        (-60, 4.0, 1.2),
        (-30, 4.3, 0.6),
        (0, 4.5, 0.4),
    ]
    lehigh_series = [
        (-180, 5.0, 0.0),
        (-150, 5.1, 0.2),
        (-120, 5.4, 0.6),
        (-90, 6.0, 1.2),
        (-60, 6.9, 1.8),
        (-30, 7.6, 1.4),
        (0, 8.1, 1.0),
    ]
    if mode == "replay":
        # extend the series through peak and recovery for replay scrubbing
        monocacy_series += [(60, 4.6, 0.2), (180, 4.0, -0.3), (300, 3.2, -0.5), (480, 2.5, -0.4)]
        lehigh_series += [(60, 8.6, 0.6), (180, 8.2, -0.2), (300, 6.5, -0.9), (480, 5.2, -0.7)]

    for offset, ft, trend in monocacy_series:
        scenario.sensors.append(
            SensorObservation(
                id=f"sensor-monocacy-{offset}",
                sensor_id="fac-gauge-monocacy",
                sensor_name="Monocacy Creek near Bethlehem (demo gauge)",
                sensor_type="river_gauge",
                geometry=GeoPoint(coordinates=(-75.3780, 40.6280)),
                observed_at=t(offset),
                value=ft,
                unit="ft",
                trend_per_hour=trend,
                is_anomalous=False,
                provenance=_prov(
                    SourceName.USGS_WATER, "USGS Water Data (demo)", t(offset), retrieved_at, status
                ),
            )
        )
    for offset, ft, trend in lehigh_series:
        scenario.sensors.append(
            SensorObservation(
                id=f"sensor-lehigh-{offset}",
                sensor_id="fac-gauge-lehigh",
                sensor_name="Lehigh River at Bethlehem (demo gauge)",
                sensor_type="river_gauge",
                geometry=GeoPoint(coordinates=(-75.3730, 40.6230)),
                observed_at=t(offset),
                value=ft,
                unit="ft",
                trend_per_hour=trend,
                is_anomalous=False,
                provenance=_prov(
                    SourceName.USGS_WATER, "USGS Water Data (demo)", t(offset), retrieved_at, status
                ),
            )
        )

    # Deliberately scoped to the Monocacy Creek confluence / Hill-to-Hill
    # Bridge area rather than all of Bethlehem, so that Lehigh University and
    # St. Luke's Hospital sit just outside it (matching the section 8 example
    # of "no confirmed severe local impact" at the university) while still
    # covering the Hill-to-Hill crossing.
    warning_polygon = GeoPolygon(
        coordinates=[[
            (-75.392, 40.614),
            (-75.362, 40.614),
            (-75.362, 40.634),
            (-75.392, 40.634),
            (-75.392, 40.614),
        ]]
    )

    # --- Alert ------------------------------------------------------------
    scenario.alerts = [
        Alert(
            id="alert-ffw-bethlehem",
            alert_id="alert-ffw-bethlehem",
            hazard_type=HazardType.FLASH_FLOOD,
            headline="Flash Flood Warning - Bethlehem area (demo)",
            description=(
                "Demonstration alert modeled on NWS Flash Flood Warning products. "
                "Heavy rainfall combined with rising creek and river levels may "
                "cause flooding of low-lying roads near waterways."
            ),
            severity=Severity.SEVERE,
            certainty=CertaintyClass.OFFICIAL_ALERT,
            urgency=Urgency.IMMEDIATE,
            effective_at=t(-60),
            expires_at=t(180) if mode == "replay" else t(180),
            geometry=warning_polygon,
            area_description="Bethlehem area, Northampton/Lehigh County line (demo)",
            provenance=_prov(
                SourceName.NWS,
                "National Weather Service (demo)",
                t(-60),
                retrieved_at,
                status,
                url="https://www.weather.gov",
            ),
        )
    ]

    # --- Forecast -----------------------------------------------------------
    scenario.forecasts = [
        Forecast(
            id="forecast-heavy-rain-1",
            forecast_id="forecast-heavy-rain-1",
            hazard_type=HazardType.FLOOD,
            issued_at=t(-45),
            valid_from=t(0),
            valid_to=t(360),
            geometry=warning_polygon,
            headline="Heavy rainfall possible through this evening (demo forecast)",
            detail=(
                "Official quantitative precipitation forecasts suggest additional "
                "rainfall over already-elevated streams. Confidence is moderate; "
                "models show some disagreement on total accumulation."
            ),
            confidence_note="moderate",
            provenance=_prov(
                SourceName.NWS, "National Weather Service (demo)", t(-45), retrieved_at, status
            ),
        )
    ]

    # --- Hazard event roll-up (kept for /live/events feed) ------------------
    scenario.events = [
        HazardEvent(
            id="event-flood-bethlehem",
            event_id="event-flood-bethlehem",
            hazard_type=HazardType.FLASH_FLOOD,
            status=CertaintyClass.OFFICIAL_ALERT,
            headline="Flash Flood Warning - Bethlehem area (demo)",
            description="See incident 'developing-flood-bethlehem' for full context.",
            severity=Severity.SEVERE,
            certainty=CertaintyClass.OFFICIAL_ALERT,
            urgency=Urgency.IMMEDIATE,
            observed_at=t(-60),
            updated_at=t(0),
            expires_at=t(180),
            geometry=warning_polygon,
            measurements={"lehigh_river_ft": 8.1, "monocacy_creek_ft": 4.5},
            provenance=_prov(
                SourceName.NWS, "National Weather Service (demo)", t(-60), retrieved_at, status
            ),
        )
    ]

    # --- Timeline ------------------------------------------------------------
    timeline: list[TimelineEntry] = [
        TimelineEntry(
            entry_id="tl-1",
            at=t(-180),
            label="Monocacy Creek begins rising",
            detail="Demo gauge trend turns positive after sustained rainfall upstream.",
            certainty_class=CertaintyClass.OBSERVED.value,
            source="USGS Water Data (demo)",
            is_first_detection=True,
        ),
        TimelineEntry(
            entry_id="tl-2",
            at=t(-150),
            label="Flood Watch issued",
            detail="Official watch issued for the Bethlehem area ahead of forecast rainfall.",
            certainty_class=CertaintyClass.OFFICIAL_ALERT.value,
            source="National Weather Service (demo)",
        ),
        TimelineEntry(
            entry_id="tl-3",
            at=t(-90),
            label="Lehigh River gauge rising quickly",
            detail="Rate of rise increases; demo gauge shows +1.2 ft/hr.",
            certainty_class=CertaintyClass.OBSERVED.value,
            source="USGS Water Data (demo)",
        ),
        TimelineEntry(
            entry_id="tl-4",
            at=t(-60),
            label="Flash Flood Warning issued",
            detail="Warning upgraded from watch to warning for the Bethlehem area.",
            certainty_class=CertaintyClass.OFFICIAL_ALERT.value,
            source="National Weather Service (demo)",
        ),
        TimelineEntry(
            entry_id="tl-5",
            at=t(-45),
            label="Traffic slowing reported near Hill-to-Hill Bridge",
            detail="Unverified public report of slower travel near the bridge approach.",
            certainty_class=CertaintyClass.USER_REPORTED.value,
            source="Community report (demo)",
        ),
        TimelineEntry(
            entry_id="tl-6",
            at=t(-20),
            label="EarthPulse groups signals into one incident",
            detail="Event Fusion AI links the watch, warning, and two gauges into a single developing incident.",
            certainty_class=CertaintyClass.AI_INFERRED.value,
            source="EarthPulse Event Fusion AI",
        ),
        TimelineEntry(
            entry_id="tl-7",
            at=t(-10),
            label="Forecast confidence improved",
            detail="Two rainfall model runs converge, narrowing the expected accumulation range.",
            certainty_class=CertaintyClass.FORECAST.value,
            source="National Weather Service (demo)",
        ),
    ]
    if mode == "replay":
        timeline += [
            TimelineEntry(
                entry_id="tl-8",
                at=t(60),
                label="Lehigh River gauge reaches peak (demo)",
                detail="Demo gauge peaks at 8.6 ft before beginning to recede.",
                certainty_class=CertaintyClass.OBSERVED.value,
                source="USGS Water Data (demo)",
                is_peak=True,
            ),
            TimelineEntry(
                entry_id="tl-9",
                at=t(180),
                label="Minor water on Hill-to-Hill Bridge approach",
                detail="No official closure was issued; road remained passable with caution per demo record.",
                certainty_class=CertaintyClass.UNVERIFIED.value,
                source="Community report (demo)",
            ),
            TimelineEntry(
                entry_id="tl-10",
                at=t(480),
                label="Warning cancelled, conditions recovering",
                detail="Gauges recede below action stage; official warning allowed to expire.",
                certainty_class=CertaintyClass.OFFICIAL_ALERT.value,
                source="National Weather Service (demo)",
                is_recovery=True,
            ),
        ]

    incident_status = "developing" if mode == "live_demo" else "resolved"
    scenario.incident = IncidentDetail(
        incident_id="developing-flood-bethlehem",
        slug="developing-flood-bethlehem",
        title="Developing flood conditions near Bethlehem, PA",
        hazard_type=HazardType.FLASH_FLOOD,
        severity=Severity.SEVERE,
        status=incident_status,
        region_label="Bethlehem, Lehigh Valley, PA",
        center=BETHLEHEM_CENTER,
        geometry=warning_polygon,
        created_at=t(-20),
        updated_at=t(0) if mode == "live_demo" else t(480),
        overall_confidence=Confidence.MODERATE,
        one_line_summary=(
            "Two rivers near Bethlehem are rising after heavy rain, and a flash "
            "flood warning is in effect."
        ),
        related_signal_count=6,
        is_demo=True,
        description=(
            "Rainfall over the Monocacy Creek and Lehigh River watersheds has driven "
            "both gauges up sharply. A flash flood warning covers the Bethlehem area. "
            "No infrastructure failure has been confirmed; low-lying river crossings "
            "are the primary concern over the next few hours."
        ),
        timeline=timeline,
        fusion_reason=FusionReason(
            incident_id="developing-flood-bethlehem",
            matched_on=["watershed", "geometry", "time_window", "hazard_type"],
            match_confidence=Confidence.HIGH,
            related_signal_ids=[
                "alert-ffw-bethlehem",
                "forecast-heavy-rain-1",
                "sensor-monocacy--90",
                "sensor-lehigh--90",
                "tl-5",
            ],
            explanation=(
                "The flood watch/warning, both gauges, and the traffic report all fall "
                "within the same watershed and time window, and all reference the same "
                "hazard type, so Event Fusion AI grouped them into one incident."
            ),
        ),
        affected_facility_ids=[
            "fac-hill-to-hill-bridge",
            "fac-fahy-bridge",
            "fac-stlukes-bethlehem",
            "fac-lvh-muhlenberg",
            "place-lehigh-university",
        ],
        affected_population_estimate=42_000,
        sources=["National Weather Service (demo)", "USGS Water Data (demo)"],
    )

    # --- Infrastructure dependency graph (for Living Cascade) ---------------
    scenario.dependencies = [
        InfrastructureDependency(
            id="dep-1",
            dependency_id="dep-1",
            from_facility_id="place-lehigh-university",
            to_facility_id="fac-hill-to-hill-bridge",
            relationship="provides_access_to",
            strength=0.8,
            provenance=_prov(SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status),
        ),
        InfrastructureDependency(
            id="dep-2",
            dependency_id="dep-2",
            from_facility_id="fac-hill-to-hill-bridge",
            to_facility_id="fac-stlukes-bethlehem",
            relationship="provides_access_to",
            strength=0.7,
            provenance=_prov(SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status),
        ),
        InfrastructureDependency(
            id="dep-3",
            dependency_id="dep-3",
            from_facility_id="fac-fahy-bridge",
            to_facility_id="fac-stlukes-bethlehem",
            relationship="provides_access_to",
            strength=0.5,
            is_uncertain=True,
            provenance=_prov(SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status),
        ),
        InfrastructureDependency(
            id="dep-4",
            dependency_id="dep-4",
            from_facility_id="fac-bethlehem-fire-1",
            to_facility_id="fac-hill-to-hill-bridge",
            relationship="depends_on",
            strength=0.6,
            provenance=_prov(SourceName.OSM, "OpenStreetMap contributors", anchor, retrieved_at, status),
        ),
        InfrastructureDependency(
            id="dep-5",
            dependency_id="dep-5",
            from_facility_id="fac-gauge-monocacy",
            to_facility_id="fac-gauge-lehigh",
            relationship="upstream_of",
            strength=0.9,
            provenance=_prov(
                SourceName.USGS_WATER, "USGS Water Data (demo)", anchor, retrieved_at, status
            ),
        ),
    ]

    # --- Historical analogs (clearly synthetic composites) -------------------
    scenario.analogs = [
        HistoricalAnalog(
            analog_id="analog-a",
            event_name="Demo analog A: Summer convective flooding composite",
            year=2018,
            similarity_score=0.71,
            similarity_features=["hazard_type", "watershed", "season", "warning_progression"],
            what_happened_next=(
                "In this composite analog, low-lying river-crossing approaches saw brief "
                "water-over-road conditions for 2-4 hours; no confirmed structural damage."
            ),
            key_differences=["Antecedent soil moisture was lower in the analog case."],
            why_it_may_not_repeat=[
                "Current rainfall forecast totals are higher than the analog event.",
                "This is a synthetic composite for demonstration, not a verified historical record.",
            ],
            data_quality=Confidence.MODERATE,
        ),
        HistoricalAnalog(
            analog_id="analog-b",
            event_name="Demo analog B: Fast-rise tributary flood composite",
            year=2021,
            similarity_score=0.58,
            similarity_features=["gauge_trajectory", "hazard_type", "infrastructure_exposure"],
            what_happened_next=(
                "In this composite analog, a secondary bridge crossing remained usable "
                "throughout, offering an effective alternate route."
            ),
            key_differences=["Warning lead time was about 30 minutes shorter."],
            why_it_may_not_repeat=[
                "Different upstream watershed, so gauge response times may differ.",
                "This is a synthetic composite for demonstration, not a verified historical record.",
            ],
            data_quality=Confidence.LOW,
        ),
    ]

    return scenario


PLACE_DIRECTORY: dict[str, dict] = {
    "lehigh-university": {
        "place_id": "lehigh-university",
        "name": "Lehigh University",
        "center": LEHIGH_UNIVERSITY,
        "aliases": ["lehigh university", "lehigh", "lehigh univ"],
    },
    "bethlehem-pa": {
        "place_id": "bethlehem-pa",
        "name": "Bethlehem, PA",
        "center": BETHLEHEM_CENTER,
        "aliases": ["bethlehem", "bethlehem pa", "bethlehem, pennsylvania"],
    },
    "allentown-pa": {
        "place_id": "allentown-pa",
        "name": "Allentown, PA",
        "center": ALLENTOWN_CENTER,
        "aliases": ["allentown", "allentown pa"],
    },
    "easton-pa": {
        "place_id": "easton-pa",
        "name": "Easton, PA",
        "center": EASTON_CENTER,
        "aliases": ["easton", "easton pa"],
    },
    "philadelphia-pa": {
        "place_id": "philadelphia-pa",
        "name": "Philadelphia, PA",
        "center": PHILADELPHIA_CENTER,
        "aliases": ["philadelphia", "philly"],
    },
    "new-york-city": {
        "place_id": "new-york-city",
        "name": "New York City, NY",
        "center": NYC_CENTER,
        "aliases": ["new york", "new york city", "nyc"],
    },
    "fac-stlukes-bethlehem": {
        "place_id": "fac-stlukes-bethlehem",
        "name": "St. Luke's University Hospital - Bethlehem Campus",
        "center": ST_LUKES_BETHLEHEM,
        "aliases": ["st luke's", "st lukes bethlehem", "st. luke's hospital"],
    },
    "fac-lvh-muhlenberg": {
        "place_id": "fac-lvh-muhlenberg",
        "name": "Lehigh Valley Hospital - Muhlenberg",
        "center": LVH_MUHLENBERG,
        "aliases": ["lvh muhlenberg", "lehigh valley hospital"],
    },
    "fac-hill-to-hill-bridge": {
        "place_id": "fac-hill-to-hill-bridge",
        "name": "Hill-to-Hill Bridge",
        "center": HILL_TO_HILL_BRIDGE,
        "aliases": ["hill to hill bridge", "hill-to-hill"],
    },
    "fac-fahy-bridge": {
        "place_id": "fac-fahy-bridge",
        "name": "Fahy Bridge",
        "center": FAHY_BRIDGE,
        "aliases": ["fahy bridge"],
    },
}
