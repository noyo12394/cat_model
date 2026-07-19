"""Run orchestrator: the transparent CAT calculation chain (section 10).

Executes Hazard -> Exposure -> Vulnerability -> Damage -> Financial ->
Uncertainty -> Audit and assembles an immutable, reproducible ``CatModelRunResult``
with a manifest (rule 13). No language model is involved in any number here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.catmodel import (
    AttributeOrigin,
    CatModelRunResult,
    ConfidenceAssessment,
    ExposureAsset,
    FinancialTerms,
    ModelRunManifest,
    ResolutionBadge,
)
from app.schemas.common import Provenance
from app.schemas.enums import Confidence, DataStatus, SourceName
from app.services.cat.damage import compute_asset_damage
from app.services.cat.financial import apply_terms
from app.services.cat.model_auditor import audit_run
from app.services.cat.uncertainty import AssetLossSpec, monte_carlo
from app.services.cat.vulnerability import select_function

CODE_VERSION = "cat-engine@0.1.0"
HAZARD_RESOLUTION_M = 10.0


def _exposure_provenance() -> Provenance:
    return Provenance(
        source=SourceName.DEMO_ARCHIVE,
        source_organization="RiskChain demonstration exposure",
        license="Demonstration only",
        retrieved_at=datetime.now(timezone.utc),
        data_status=DataStatus.DEMO,
    )


def _confidence(audit_findings) -> ConfidenceAssessment:
    highs = [f for f in audit_findings if f.severity == "high"]
    warnings = [f for f in audit_findings if f.severity == "warning"]
    if highs:
        band = Confidence.LOW
    elif len(warnings) >= 2:
        band = Confidence.LOW
    elif warnings:
        band = Confidence.MODERATE
    else:
        band = Confidence.MODERATE
    drivers = [f.title for f in (highs + warnings)] or ["Demonstration vulnerability curves (experimental approval)"]
    largest = highs[0].title if highs else (warnings[0].title if warnings else "Vulnerability curve spread")
    return ConfidenceAssessment(band=band, drivers=drivers, largest_uncertainty=largest)


def run_flood_scenario(
    assets: list[ExposureAsset],
    depths: dict[str, float],
    terms: FinancialTerms,
    *,
    scenario_label: str,
    region_label: str,
    seed: int = 12345,
    iterations: int = 2000,
    parent_run_id: str | None = None,
) -> CatModelRunResult:
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    vfunc_by_asset = {a.asset_id: select_function(a.occupancy) for a in assets}

    asset_damage = []
    asset_financial = []
    specs: list[AssetLossSpec] = []
    for asset in assets:
        depth = depths.get(asset.asset_id, 0.0)
        vf = vfunc_by_asset[asset.asset_id]
        dmg = compute_asset_damage(asset, depth, vf)
        asset_damage.append(dmg)
        asset_financial.append(apply_terms(asset.asset_id, dmg.ground_up_loss_usd, terms))
        specs.append(
            AssetLossSpec(
                asset_id=asset.asset_id,
                replacement_value_usd=asset.replacement_value_usd,
                contents_value_usd=asset.contents_value_usd,
                business_interruption_daily_usd=asset.business_interruption_daily_usd,
                mean_building_ratio=dmg.mean_damage_ratio,
                cov=vf.damage_ratio_cov,
                terms=terms,
            )
        )

    gu_dist, gross_dist, net_dist = monte_carlo(specs, seed=seed, iterations=iterations)

    audit_findings = audit_run(
        assets, asset_damage, vfunc_by_asset,
        hazard_resolution_m=HAZARD_RESOLUTION_M,
        analysis_resolution_label="Building footprint",
    )

    sources = [_exposure_provenance()]
    seen = set()
    for vf in vfunc_by_asset.values():
        if vf.function_id not in seen:
            sources.append(vf.source)
            seen.add(vf.function_id)

    manifest = ModelRunManifest(
        run_id=run_id,
        created_at=now,
        code_version=CODE_VERSION,
        model_ids={
            "hazard": "haz-flood-depth-demo@0.1.0-demo",
            "vulnerability": "flood-depth-damage-demo@0.1.0-demo",
            "financial": "fin-terms-v1@1.0.0",
        },
        random_seed=seed,
        parameters={"iterations": iterations, "deductible_usd": terms.deductible_usd,
                    "limit_usd": terms.limit_usd if terms.limit_usd is not None else -1,
                    "coinsurance": terms.coinsurance},
        input_summary={
            "asset_count": len(assets),
            "total_replacement_value_usd": round(sum(a.replacement_value_usd for a in assets), 2),
            "mean_depth_ft": round(sum(depths.get(a.asset_id, 0.0) for a in assets) / (len(assets) or 1), 3),
        },
        parent_run_id=parent_run_id,
    )

    return CatModelRunResult(
        run_id=run_id,
        scenario_label=scenario_label,
        hazard_type="flood",
        region_label=region_label,
        is_demo=True,
        data_status=DataStatus.DEMO,
        resolution=ResolutionBadge(
            analysis_resolution="Building footprint",
            hazard_resolution="~10 m modelled depth grid (demonstration)",
            population_resolution="Not used in this run",
            building_use_origin=AttributeOrigin.MODEL_INFERRED,
        ),
        asset_count=len(assets),
        financial_terms=terms,
        ground_up_distribution=gu_dist,
        gross_distribution=gross_dist,
        net_insured_distribution=net_dist,
        asset_damage=asset_damage,
        asset_financial=asset_financial,
        confidence=_confidence(audit_findings),
        audit_findings=audit_findings,
        assumptions=[
            {"label": "Vulnerability curves", "value": "Demonstration depth-damage curves (experimental)", "origin": AttributeOrigin.MODEL_INFERRED},
            {"label": "Contents damage", "value": "1.15x structural ratio, capped at 1.0", "origin": AttributeOrigin.DEFAULT_ASSUMPTION},
            {"label": "Downtime", "value": "Up to 180 days scaled by structural damage ratio", "origin": AttributeOrigin.DEFAULT_ASSUMPTION},
            {"label": "Hazard", "value": "Modelled 100-year depth-at-structure, not a FEMA flood zone", "origin": AttributeOrigin.MODEL_INFERRED},
        ],
        sources=sources,
        limitations=[
            "All values are demonstration outputs; the vulnerability curves are not production-approved.",
            "Depth-at-structure is a synthetic surface, not a hydraulic model or survey.",
            "Loss is economic ground-up plus insured views; it is not an underwriting-grade estimate.",
            "First-floor elevations are default assumptions, not surveyed values - a major flood-loss uncertainty.",
        ],
        manifest=manifest,
    )
