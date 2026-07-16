"""Explainable compound-hazard demonstration service.

The service deliberately returns a research-preview demonstration rather than
claiming that recent research prototypes are operational. Its outputs combine
the existing seeded flood signals with deterministic consequence rules. Every
record is labeled ``demo`` and carries plain-language limitations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.memory_repository import MemoryRepository
from app.schemas.compound import (
    CompoundEventSummary,
    ConsequenceStep,
    EvidenceChannel,
    HazardSignalSummary,
    PossibleFuture,
    VerificationPriority,
)
from app.schemas.enums import CertaintyClass, Confidence, DataStatus, Severity


def build_compound_events(repo: MemoryRepository) -> list[CompoundEventSummary]:
    incident = repo.get_incident("developing-flood-bethlehem", mode="live")
    sensors = repo.list_sensors(mode="live")
    alerts = repo.list_alerts(mode="live")
    now = datetime.now(timezone.utc)

    rising = [sensor for sensor in sensors if (sensor.trend_per_hour or 0) > 0.3]
    latest_river = rising[-1] if rising else (sensors[-1] if sensors else None)
    alert = alerts[0] if alerts else None

    signals = [
        HazardSignalSummary(
            signal_id=alert.alert_id if alert else "demo-heavy-rain-alert",
            hazard_type="severe_weather",
            label="Heavy-rain warning",
            source="National Weather Service (demo fixture)",
            data_status=DataStatus.DEMO,
            certainty=CertaintyClass.OFFICIAL_ALERT,
            severity=Severity.SEVERE,
            center=(-75.3705, 40.6259),
            observed_at=alert.effective_at if alert else now,
            detail="A seeded warning supplies the official-alert role in this demonstration.",
        ),
        HazardSignalSummary(
            signal_id=latest_river.id if latest_river else "demo-rising-river",
            hazard_type="flood",
            label="River level rising",
            source="USGS Water (demo gauge)",
            data_status=DataStatus.DEMO,
            certainty=CertaintyClass.OBSERVED,
            severity=Severity.ELEVATED,
            center=(-75.3730, 40.6230),
            observed_at=latest_river.observed_at if latest_river else now,
            detail=(
                f"Seeded gauge value {latest_river.value:g} {latest_river.unit}; "
                f"trend {latest_river.trend_per_hour:+g} {latest_river.unit}/hr."
                if latest_river and latest_river.trend_per_hour is not None
                else "Seeded gauge trend is elevated."
            ),
        ),
        HazardSignalSummary(
            signal_id="demo-saturated-ground",
            hazard_type="landslide",
            label="Ground already saturated",
            source="EarthPulse demonstration context",
            data_status=DataStatus.DEMO,
            certainty=CertaintyClass.SIMULATED,
            severity=Severity.WATCH,
            center=(-75.3860, 40.6190),
            observed_at=now,
            detail="Demonstration context used to show how compound-hazard reasoning is explained.",
        ),
    ]

    return [
        CompoundEventSummary(
            event_id="compound-flood-access-bethlehem",
            title="Rainfall, river rise, and access pressure",
            region_label=incident.region_label if incident else "Bethlehem, Pennsylvania",
            status="developing research demo",
            center=(-75.3705, 40.6259),
            hazards=["severe_weather", "flood", "landslide"],
            data_status=DataStatus.DEMO,
            is_demo=True,
            fusion_confidence=Confidence.MODERATE,
            fusion_explanation=(
                "Three signals overlap in place and time. The combination matters because rising water "
                "and already-wet ground can affect the same limited set of river crossings."
            ),
            matched_on=["place", "time window", "watershed", "shared infrastructure"],
            signals=signals,
            consequence_chain=[
                ConsequenceStep(
                    step_id="observed-rain-river",
                    label="Heavy rain and river rise",
                    detail="Official-alert and gauge roles agree that conditions are changing.",
                    certainty=CertaintyClass.OBSERVED,
                    confidence=Confidence.HIGH,
                    time_window="Now",
                ),
                ConsequenceStep(
                    step_id="forecast-crossing",
                    label="Low crossing may become difficult to use",
                    detail="Forecast boundary overlaps a low-lying approach; no closure is confirmed.",
                    certainty=CertaintyClass.FORECAST,
                    confidence=Confidence.MODERATE,
                    time_window="Next 1–3 hours",
                ),
                ConsequenceStep(
                    step_id="inferred-route",
                    label="Hospital route may become longer",
                    detail="The dependency graph has fewer practical alternatives south of the river.",
                    certainty=CertaintyClass.AI_INFERRED,
                    confidence=Confidence.MODERATE,
                    time_window="If the crossing is disrupted",
                ),
                ConsequenceStep(
                    step_id="inferred-coverage",
                    label="Emergency coverage may become less reliable",
                    detail="This is a modeled service consequence, not a confirmed operational impact.",
                    certainty=CertaintyClass.AI_INFERRED,
                    confidence=Confidence.LOW,
                    time_window="Possible downstream effect",
                ),
            ],
            possible_futures=[
                PossibleFuture(
                    future_id="limited",
                    label="Limited local disruption",
                    support="most_supported",
                    detail="River rise slows and both main crossings remain usable.",
                    consequence="Monitor low approaches; no confirmed service disruption.",
                    distinguishing_signal="The next two gauge readings flatten.",
                ),
                PossibleFuture(
                    future_id="crossing",
                    label="One crossing affected",
                    support="plausible",
                    detail="Water reaches a low approach and traffic shifts to an alternative crossing.",
                    consequence="Hospital travel time may increase; route confidence falls.",
                    distinguishing_signal="Gauge rise continues and a road observation confirms water.",
                ),
                PossibleFuture(
                    future_id="network",
                    label="Network stress case",
                    support="stress_case",
                    detail="Two crossings are constrained during the same time window.",
                    consequence="Emergency coverage south of the river may become less reliable.",
                    distinguishing_signal="Continued rainfall plus two independent road confirmations.",
                ),
            ],
            evidence_agreement=[
                EvidenceChannel(
                    channel="Official alert",
                    agreement="supports",
                    detail="Seeded flood warning supports the heavy-rain signal.",
                    data_status=DataStatus.DEMO,
                ),
                EvidenceChannel(
                    channel="River gauges",
                    agreement="supports",
                    detail=f"{len(rising)} seeded observations show an elevated rising trend.",
                    data_status=DataStatus.DEMO,
                ),
                EvidenceChannel(
                    channel="Satellite / radar change",
                    agreement="unavailable",
                    detail="No verified before/after imagery is connected to this demonstration.",
                    data_status=DataStatus.UNAVAILABLE,
                ),
                EvidenceChannel(
                    channel="Road confirmation",
                    agreement="unavailable",
                    detail="No official closure or current road-camera confirmation.",
                    data_status=DataStatus.UNAVAILABLE,
                ),
            ],
            next_checks=[
                VerificationPriority(
                    rank=1,
                    label="Verify the low crossing",
                    why="A current road observation would separate the limited and crossing-impact futures.",
                    expected_value="Largest expected reduction in route uncertainty",
                    action="Request an approved road-camera or field observation",
                ),
                VerificationPriority(
                    rank=2,
                    label="Refresh both river gauges",
                    why="A second trend reading tests whether the rise is continuing or flattening.",
                    expected_value="High value for the 1–3 hour outlook",
                    action="Retrieve the next authoritative USGS observations",
                ),
                VerificationPriority(
                    rank=3,
                    label="Retrieve radar before/after imagery",
                    why="Radar can help distinguish possible new water from permanent water and cloud cover.",
                    expected_value="Medium value; human verification still required",
                    action="Queue a validated Sentinel-1 comparison workflow",
                ),
            ],
            limitations=[
                "This compound event is a synthetic research demonstration, not current conditions.",
                "No live road closure, satellite change detection, or surveyed bridge elevation is connected.",
                "Possible futures are qualitative branches, not calibrated probabilities.",
                "Recent research ideas shown here are prototypes and require operational validation.",
            ],
        )
    ]
