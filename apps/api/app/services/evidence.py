"""Evidence Trail assembly (section 23): full lineage for an incident's claims."""

from __future__ import annotations

from app.db.memory_repository import MemoryRepository
from app.schemas.common import EvidenceItem, EvidenceTrail, ModelBasis
from app.schemas.enums import CertaintyClass, Confidence
from app.schemas.incident import IncidentDetail
from app.services.impact_nowcast import build_impact_sequence


def build_incident_evidence(incident: IncidentDetail, repo: MemoryRepository, mode: str = "live") -> list[EvidenceTrail]:
    trails: list[EvidenceTrail] = []

    if incident.fusion_reason:
        trails.append(
            EvidenceTrail(
                claim=f"'{incident.title}' is one developing incident",
                certainty_class=CertaintyClass.AI_INFERRED,
                confidence=incident.fusion_reason.match_confidence,
                supporting_evidence=[
                    EvidenceItem(label=f"Matched on: {', '.join(incident.fusion_reason.matched_on)}"),
                    EvidenceItem(label=f"{len(incident.fusion_reason.related_signal_ids)} related signal(s)"),
                ],
                weaknesses=["Fusion rules use simple time/location/hazard-type matching, not a learned model."],
                model_basis=ModelBasis(
                    model_id="event-fusion",
                    model_version="0.2",
                    run_at=incident.updated_at,
                    inputs_used=["alerts", "sensor_observations", "reports", "watershed_tags"],
                ),
                plain_language_summary=incident.fusion_reason.explanation,
            )
        )

    sequence = build_impact_sequence(incident, repo, mode=mode)
    for step in sequence.steps:
        trails.append(step.evidence_trail)

    return trails
