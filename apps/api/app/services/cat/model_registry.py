"""Model registry (section 11).

A formal, inspectable record of every model the CAT engine can run, with its
approval status, limitations and what it is *not* intended for. The AI copilot
and API may only run production/experimental-approved models from here.
"""

from __future__ import annotations

from app.schemas.catmodel import ApprovalStatus, ModelRegistryEntry
from app.services.cat.vulnerability import VULNERABILITY_FUNCTIONS

_ENGINE_MODELS: list[ModelRegistryEntry] = [
    ModelRegistryEntry(
        model_id="haz-flood-depth-demo",
        name="Flood depth-at-structure (demonstration footprint)",
        provider="RiskChain (demonstration)",
        hazard="flood",
        geography="Lehigh Valley, PA (demo)",
        geographic_resolution="Per-structure sampled depth (demo)",
        asset_classes=["all"],
        intensity_measure="flood_depth_ft",
        outputs=["depth_at_structure_ft"],
        version="0.1.0-demo",
        calibration_dataset="Synthetic demonstration footprint",
        validation_geography="None - demonstration only",
        peer_reviewed_source=None,
        doi=None,
        known_limitations=[
            "Depths are a synthetic demonstration surface, not a hydraulic model output.",
            "A flood-zone designation is not a flood depth; this is depth, not a FEMA zone.",
        ],
        approval_status=ApprovalStatus.APPROVED_EXPERIMENTAL,
        not_intended_for=["Regulatory determinations", "Property-specific underwriting"],
    ),
    ModelRegistryEntry(
        model_id="fin-terms-v1",
        name="Location financial terms (deductible/limit/coinsurance)",
        provider="RiskChain",
        hazard="all",
        geography="Global",
        geographic_resolution="Per-asset",
        asset_classes=["all"],
        intensity_measure="n/a",
        outputs=["ground_up", "gross", "net_insured"],
        version="1.0.0",
        calibration_dataset="n/a (deterministic policy arithmetic)",
        validation_geography="Unit-tested invariants",
        peer_reviewed_source=None,
        doi=None,
        known_limitations=["Occurrence-level terms only; no aggregate/reinstatement terms in the MVP."],
        approval_status=ApprovalStatus.APPROVED_PRODUCTION,
        not_intended_for=["Complex layered treaty structures"],
    ),
    ModelRegistryEntry(
        model_id="prob-eventset-demo",
        name="Flood event-set simulator (AAL/OEP/AEP/VaR/TVaR)",
        provider="RiskChain (demonstration)",
        hazard="flood",
        geography="Lehigh Valley, PA (demo)",
        geographic_resolution="Portfolio",
        asset_classes=["all"],
        intensity_measure="flood_depth_ft",
        outputs=["AAL", "OEP", "AEP", "VaR", "TVaR"],
        version="0.1.0-demo",
        calibration_dataset="Synthetic demonstration event set",
        validation_geography="None - demonstration only",
        peer_reviewed_source=None,
        doi=None,
        known_limitations=[
            "Independent Poisson events; no spatial correlation or clustering.",
            "Demonstration rates and severities, not a calibrated catalogue.",
        ],
        approval_status=ApprovalStatus.APPROVED_EXPERIMENTAL,
        not_intended_for=["Capital modelling", "Reinsurance pricing"],
    ),
]


def _vulnerability_entries() -> list[ModelRegistryEntry]:
    entries: list[ModelRegistryEntry] = []
    for vf in VULNERABILITY_FUNCTIONS.values():
        entries.append(
            ModelRegistryEntry(
                model_id=vf.function_id,
                name=vf.name,
                provider=vf.source.source_organization,
                hazard=vf.hazard,
                geography="Demonstration",
                geographic_resolution="Per-asset",
                asset_classes=[vf.asset_class],
                intensity_measure=vf.intensity_measure.name,
                outputs=["mean_damage_ratio", "damage_state_probabilities"],
                version=vf.version,
                calibration_dataset="Representative demonstration curve",
                validation_geography="None - demonstration only",
                peer_reviewed_source=None,
                doi=None,
                known_limitations=[vf.prohibited_extrapolations, vf.applicability_notes],
                approval_status=vf.approval_status,
                not_intended_for=["Production loss estimation until reviewed and approved"],
            )
        )
    return entries


def list_models() -> list[ModelRegistryEntry]:
    return _ENGINE_MODELS + _vulnerability_entries()


def get_model(model_id: str) -> ModelRegistryEntry | None:
    return next((m for m in list_models() if m.model_id == model_id), None)
