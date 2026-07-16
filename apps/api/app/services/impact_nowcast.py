"""Impact Nowcasting AI (section 31.2 / signature feature 11).

Combines OFFICIAL forecasts/alerts and OBSERVED sensor trends to estimate
short-term consequences. It never invents a weather forecast - rainfall and
warning inputs always come from the alert/forecast records already in the
incident; this service only reasons about their downstream infrastructure
consequences using explicit, inspectable rules (interpretable-by-design,
per section 31.2's "start with interpretable models" guidance - no ML model
is warranted yet at this data volume).

Confidence deliberately DECREASES the further downstream (more inferential)
a step is: a rising gauge is observed fact; "emergency coverage may be less
reliable" is two inferential hops away and should read as less certain.
"""

from __future__ import annotations

from datetime import timedelta

from app.db.memory_repository import MemoryRepository
from app.schemas.common import EvidenceItem, EvidenceTrail, ModelBasis, TimeRange
from app.schemas.enums import CertaintyClass, Confidence, FacilityType
from app.schemas.incident import IncidentDetail
from app.schemas.inference import ImpactSequence, ImpactStep

RISING_TREND_THRESHOLD_FT_PER_HR = 0.5


def _latest_by_sensor(repo: MemoryRepository, mode: str) -> dict[str, "object"]:
    latest: dict[str, object] = {}
    for obs in repo.list_sensors(mode=mode):
        if obs.sensor_id not in latest or obs.observed_at > latest[obs.sensor_id].observed_at:  # type: ignore[attr-defined]
            latest[obs.sensor_id] = obs
    return latest


def build_impact_sequence(
    incident: IncidentDetail, repo: MemoryRepository, mode: str = "live"
) -> ImpactSequence:
    latest_sensors = _latest_by_sensor(repo, mode="replay" if mode == "replay" else "live_demo")
    rising = [
        s
        for s in latest_sensors.values()
        if (s.trend_per_hour or 0) >= RISING_TREND_THRESHOLD_FT_PER_HR  # type: ignore[attr-defined]
    ]

    affected = [repo.get_facility(fid) for fid in incident.affected_facility_ids]
    affected = [f for f in affected if f is not None]
    crossings = [f for f in affected if f.facility_type in (FacilityType.BRIDGE, FacilityType.RIVER_CROSSING)]
    hospitals = [f for f in affected if f.facility_type == FacilityType.HOSPITAL]
    fire_stations = [f for f in affected if f.facility_type == FacilityType.FIRE_STATION]

    alerts = repo.list_alerts(mode="replay" if mode == "replay" else "live")
    active_alert = alerts[0] if alerts else None

    steps: list[ImpactStep] = []
    now = incident.updated_at
    model_basis = ModelBasis(
        model_id="impact-nowcast",
        model_version="0.3",
        run_at=now,
        inputs_used=[
            "active_alert",
            "river_gauge_trend",
            "affected_facility_list",
            "infrastructure_dependency_graph",
        ],
    )

    if rising and active_alert and crossings:
        gauge_names = ", ".join(s.sensor_name for s in rising)  # type: ignore[attr-defined]
        steps.append(
            ImpactStep(
                step_id="step-1",
                order=1,
                statement="Water may reach a low-lying road near the rising gauge(s).",
                time_window=TimeRange(start=now, end=now + timedelta(hours=2), label="Next 1-2 hours"),
                confidence=Confidence.MODERATE,
                evidence_trail=EvidenceTrail(
                    claim="Low-lying road may see water encroachment",
                    certainty_class=CertaintyClass.AI_INFERRED,
                    confidence=Confidence.MODERATE,
                    supporting_evidence=[
                        EvidenceItem(label=f"Active alert: {active_alert.headline}"),
                        EvidenceItem(label=f"Rising gauge(s): {gauge_names}"),
                    ],
                    weaknesses=[
                        "No road-camera confirmation available.",
                        "Road elevation for nearby crossings is estimated, not surveyed.",
                    ],
                    model_basis=model_basis,
                    plain_language_summary=(
                        "Two things point the same way: an active flood warning and gauges "
                        "that are rising quickly. That combination often reaches low roads first."
                    ),
                ),
            )
        )

    if steps and crossings:
        crossing_names = ", ".join(f.name for f in crossings)
        steps.append(
            ImpactStep(
                step_id="step-2",
                order=2,
                statement=f"{crossing_names} may become difficult to use.",
                time_window=TimeRange(start=now, end=now + timedelta(hours=3), label="Next 1-3 hours"),
                confidence=Confidence.MODERATE,
                evidence_trail=EvidenceTrail(
                    claim=f"{crossing_names} closure risk is elevated",
                    certainty_class=CertaintyClass.AI_INFERRED,
                    confidence=Confidence.MODERATE,
                    supporting_evidence=[
                        EvidenceItem(label="Step 1: possible water on low-lying road"),
                        EvidenceItem(label="Crossing approach elevation is low relative to gauge datum (estimated)"),
                    ],
                    weaknesses=[
                        "No official closure has been issued.",
                        "Elevation figures are estimated, not from a survey-grade source.",
                    ],
                    model_basis=model_basis,
                    plain_language_summary=(
                        "If water reaches the road, the crossing itself is the next thing "
                        "affected. No closure is confirmed yet."
                    ),
                ),
            )
        )

    if steps and crossings and hospitals:
        hospital_names = ", ".join(h.name for h in hospitals)
        steps.append(
            ImpactStep(
                step_id="step-3",
                order=3,
                statement=f"Travel time to {hospital_names} may increase.",
                time_window=TimeRange(start=now, end=now + timedelta(hours=4), label="Next 2-4 hours"),
                confidence=Confidence.LOW,
                evidence_trail=EvidenceTrail(
                    claim="Hospital access travel time may increase",
                    certainty_class=CertaintyClass.AI_INFERRED,
                    confidence=Confidence.LOW,
                    supporting_evidence=[
                        EvidenceItem(label="Step 2: crossing(s) may become difficult to use"),
                        EvidenceItem(label="Dependency graph: hospital access routes rely on the affected crossing(s)"),
                    ],
                    weaknesses=[
                        "Assumes drivers reroute rather than wait; real behavior varies.",
                        "Does not account for live traffic conditions.",
                    ],
                    model_basis=model_basis,
                    plain_language_summary=(
                        "This is two inferential steps removed from what's actually observed, "
                        "so treat it as a lower-confidence possibility to watch, not a prediction."
                    ),
                ),
            )
        )

    if steps and fire_stations and crossings:
        station_names = ", ".join(f.name for f in fire_stations)
        steps.append(
            ImpactStep(
                step_id="step-4",
                order=4,
                statement=f"Emergency coverage from {station_names} may become less reliable in the affected area.",
                time_window=TimeRange(start=now, end=now + timedelta(hours=4), label="Next 2-4 hours"),
                confidence=Confidence.LOW,
                evidence_trail=EvidenceTrail(
                    claim="Emergency response coverage may be reduced",
                    certainty_class=CertaintyClass.AI_INFERRED,
                    confidence=Confidence.LOW,
                    supporting_evidence=[
                        EvidenceItem(label="Step 2: crossing(s) may become difficult to use"),
                        EvidenceItem(label="Dependency graph: this station's coverage area relies on the affected crossing(s)"),
                    ],
                    weaknesses=[
                        "Does not model crew repositioning or mutual aid.",
                        "Coverage-area boundaries are approximate.",
                    ],
                    model_basis=model_basis,
                    plain_language_summary=(
                        "This is the most speculative step in the sequence - three hops from "
                        "the observed data - and should be treated as something to monitor."
                    ),
                ),
            )
        )

    overall = Confidence.MODERATE if len(steps) <= 2 else Confidence.LOW
    return ImpactSequence(
        incident_id=incident.incident_id,
        title="Developing flood sequence",
        observed_signals=[
            active_alert.headline if active_alert else "No active alert",
            *[f"{s.sensor_name} rising" for s in rising],  # type: ignore[attr-defined]
        ],
        steps=steps,
        overall_confidence=overall,
        model_basis=model_basis,
    )
