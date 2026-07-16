"""Find Hidden Risks (section 30) - a defining professional feature.

Scans the facility/dependency graph and sensor set for concrete, explainable
risk patterns rather than a single opaque score. Every finding cites the
evidence behind it (a specific facility, a specific missing field, a
specific graph structure) so a user can act on it.
"""

from __future__ import annotations

import networkx as nx
from pydantic import BaseModel

from app.db.memory_repository import MemoryRepository
from app.schemas.enums import FacilityType
from app.services.cascade import build_graph
from app.services.sensor_health import check_sensor_health

DATA_COMPLETENESS_THRESHOLD = 0.6


class HiddenRisk(BaseModel):
    risk_id: str
    category: str
    title: str
    detail: str
    evidence: list[str]
    severity_rank: int  # 1 = highest


def find_hidden_risks(repo: MemoryRepository) -> list[HiddenRisk]:
    risks: list[HiddenRisk] = []
    graph = build_graph(repo)
    hospitals = [f for f in repo.list_facilities() if f.facility_type == FacilityType.HOSPITAL]
    origin_candidates = [f.facility_id for f in repo.list_facilities() if f.facility_type == FacilityType.SCHOOL]

    # 1. Single points of failure: bridges whose removal disconnects a
    #    hospital from every school/origin node in the dependency graph.
    for facility in repo.list_facilities():
        if facility.facility_type not in (FacilityType.BRIDGE, FacilityType.RIVER_CROSSING):
            continue
        reduced = graph.copy()
        if reduced.has_node(facility.facility_id):
            reduced.remove_node(facility.facility_id)
        for hospital in hospitals:
            if not reduced.has_node(hospital.facility_id):
                continue
            still_reachable = any(
                reduced.has_node(origin) and nx.has_path(reduced, origin, hospital.facility_id)
                for origin in origin_candidates
                if reduced.has_node(origin)
            )
            was_reachable = any(
                graph.has_node(origin) and nx.has_path(graph, origin, hospital.facility_id)
                for origin in origin_candidates
            )
            if was_reachable and not still_reachable:
                risks.append(
                    HiddenRisk(
                        risk_id=f"spof-{facility.facility_id}-{hospital.facility_id}",
                        category="single_point_of_failure",
                        title=f"{facility.name} is a single point of failure for {hospital.name} access",
                        detail=(
                            f"In the seeded dependency graph, removing {facility.name} leaves no "
                            f"modeled path to {hospital.name}. A redundant route is not represented."
                        ),
                        evidence=[
                            f"Facility: {facility.name} ({facility.facility_type.value})",
                            f"Dependent facility: {hospital.name}",
                        ],
                        severity_rank=1,
                    )
                )

    # 2. Poor monitoring / incomplete attribute data.
    for facility in repo.list_facilities():
        if facility.data_completeness < DATA_COMPLETENESS_THRESHOLD:
            risks.append(
                HiddenRisk(
                    risk_id=f"poor-monitoring-{facility.facility_id}",
                    category="poor_monitoring",
                    title=f"{facility.name} has incomplete attribute data",
                    detail=(
                        f"Only {facility.data_completeness * 100:.0f}% of expected attributes are "
                        "known for this facility, which limits how confidently it can be assessed."
                    ),
                    evidence=[f"data_completeness = {facility.data_completeness:.2f}"],
                    severity_rank=3,
                )
            )

    # 3. Sensor health issues (stale, frozen, jumpy) feed straight in.
    for flag in check_sensor_health(repo, mode="live"):
        risks.append(
            HiddenRisk(
                risk_id=f"sensor-{flag.sensor_id}-{flag.issue}",
                category="sensor_health",
                title=f"{flag.sensor_name}: {flag.issue.replace('_', ' ')}",
                detail=flag.detail,
                evidence=[f"sensor_id = {flag.sensor_id}", f"issue = {flag.issue}"],
                severity_rank=2,
            )
        )

    # 4. High exposure + low data quality combination.
    for facility in repo.list_facilities():
        if facility.facility_type == FacilityType.HOSPITAL and facility.backup_power is None:
            risks.append(
                HiddenRisk(
                    risk_id=f"unknown-backup-power-{facility.facility_id}",
                    category="high_risk_low_data_quality",
                    title=f"Backup power status unknown for {facility.name}",
                    detail=(
                        "This hospital is near the active hazard area, but backup-power "
                        "information is not available in this dataset."
                    ),
                    evidence=["backup_power = unknown", "facility_type = hospital"],
                    severity_rank=1,
                )
            )

    risks.sort(key=lambda r: r.severity_rank)
    return risks
