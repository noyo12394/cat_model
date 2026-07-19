"""Operational views over immutable CAT model runs.

This module deliberately derives every comparison, map layer and report from a
stored ``CatModelRunResult``. It never asks an LLM to calculate or fill missing
values. The API can therefore expose richer professional workflows without
creating a second, unaudited calculation path.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.data.demo.lehigh_valley_exposure import build_demo_exposure
from app.schemas.catmodel import (
    AttributeOrigin,
    CapabilityCoverage,
    CapabilityStatus,
    CatModelRunResult,
    DataCoverageItem,
    ModelResultLayer,
    ModelRunComparison,
    ReportSection,
    RunComparisonMetric,
    StructuredRunReport,
)
from app.schemas.enums import DataStatus


def compare_runs(
    baseline: CatModelRunResult,
    comparison: CatModelRunResult,
) -> ModelRunComparison:
    """Compare two immutable runs using their recorded distributions."""

    metric_specs = [
        ("ground_up_p50", baseline.ground_up_distribution.p50_usd, comparison.ground_up_distribution.p50_usd),
        ("ground_up_p90", baseline.ground_up_distribution.p90_usd, comparison.ground_up_distribution.p90_usd),
        ("gross_p50", baseline.gross_distribution.p50_usd, comparison.gross_distribution.p50_usd),
        ("net_insured_p50", baseline.net_insured_distribution.p50_usd, comparison.net_insured_distribution.p50_usd),
    ]
    metrics = []
    for label, before, after in metric_specs:
        delta = after - before
        metrics.append(RunComparisonMetric(
            metric=label,
            baseline_value=round(before, 2),
            comparison_value=round(after, 2),
            absolute_change=round(delta, 2),
            percent_change=round(100 * delta / before, 2) if before else None,
            unit="USD",
        ))

    changed: list[str] = []
    for field in ("deductible_usd", "limit_usd", "coinsurance"):
        before = getattr(baseline.financial_terms, field)
        after = getattr(comparison.financial_terms, field)
        if before != after:
            changed.append(f"{field}: {before} -> {after}")
    if baseline.manifest.random_seed != comparison.manifest.random_seed:
        changed.append(f"random_seed: {baseline.manifest.random_seed} -> {comparison.manifest.random_seed}")
    if baseline.manifest.parameters.get("iterations") != comparison.manifest.parameters.get("iterations"):
        changed.append(
            "iterations: "
            f"{baseline.manifest.parameters.get('iterations')} -> {comparison.manifest.parameters.get('iterations')}"
        )

    direction = next(metric.absolute_change for metric in metrics if metric.metric == "ground_up_p50")
    interpretation = [
        "The comparison uses recorded model outputs; it does not recalculate either run.",
        (
            "Median ground-up loss increased in the comparison run."
            if direction > 0
            else "Median ground-up loss decreased in the comparison run."
            if direction < 0
            else "Median ground-up loss is unchanged between the runs."
        ),
    ]
    return ModelRunComparison(
        baseline_run_id=baseline.run_id,
        comparison_run_id=comparison.run_id,
        metrics=metrics,
        changed_assumptions=changed or ["No tracked financial or simulation parameter changed."],
        interpretation=interpretation,
        limitations=[
            "Both runs use the same synthetic demonstration hazard and exposure unless their manifests state otherwise.",
            "A difference is a model-output comparison, not evidence that an intervention caused the change.",
        ],
    )


def result_layer(run: CatModelRunResult, layer_id: str) -> ModelResultLayer:
    """Create a GeoJSON layer from the exact asset-level output of a run."""

    assets = {asset.asset_id: asset for asset in build_demo_exposure()}
    damage = {item.asset_id: item for item in run.asset_damage}
    finance = {item.asset_id: item for item in run.asset_financial}
    definitions = {
        "damage-ratio": ("Mean structural damage ratio", "mean_damage_ratio", "ratio"),
        "ground-up-loss": ("Ground-up loss by asset", "ground_up_loss_usd", "USD"),
        "insured-loss": ("Net insured loss by asset", "net_insured_loss_usd", "USD"),
        "flood-depth": ("Modelled flood depth at asset", "intensity", "ft"),
    }
    if layer_id not in definitions:
        raise KeyError(layer_id)
    title, value_field, unit = definitions[layer_id]

    features = []
    for asset_id, asset in assets.items():
        d = damage[asset_id]
        f = finance[asset_id]
        value = {
            "mean_damage_ratio": d.mean_damage_ratio,
            "ground_up_loss_usd": d.ground_up_loss_usd,
            "net_insured_loss_usd": f.net_insured_loss_usd,
            "intensity": d.intensity,
        }[value_field]
        features.append({
            "type": "Feature",
            "id": asset_id,
            "geometry": {"type": "Point", "coordinates": list(asset.center)},
            "properties": {
                "asset_id": asset_id,
                "name": asset.name,
                "occupancy": asset.occupancy,
                "value": round(value, 4 if unit == "ratio" else 2),
                "unit": unit,
                "data_status": run.data_status.value,
                "attribute_origin": "modelled_demo",
                "extrapolated": d.extrapolated,
            },
        })

    return ModelResultLayer(
        run_id=run.run_id,
        layer_id=layer_id,
        title=title,
        geometry_type="Point",
        data_status=run.data_status,
        geojson={"type": "FeatureCollection", "features": features},
        value_field="value",
        value_unit=unit,
        provenance_note="Derived from the immutable asset results in this run; coordinates come from the demonstration exposure.",
        limitations=[
            "Points represent demonstration assets, not a complete building inventory.",
            "Flood depth is synthetic and damage functions are experimental, not production-approved.",
        ],
    )


def build_report(run: CatModelRunResult, report_type: str) -> StructuredRunReport:
    """Build a source-linked report object without generated scientific claims."""

    money = lambda value: f"${value / 1_000_000:.2f} million"  # noqa: E731
    common = [
        ReportSection(
            section_id="result",
            title="Modelled loss range",
            statements=[
                f"Ground-up loss p10-p90: {money(run.ground_up_distribution.p10_usd)} to {money(run.ground_up_distribution.p90_usd)}.",
                f"Median ground-up estimate: {money(run.ground_up_distribution.p50_usd)}.",
                f"Confidence: {run.confidence.band.value}; largest uncertainty: {run.confidence.largest_uncertainty}.",
            ],
            data_references=["ground_up_distribution", "confidence"],
        ),
        ReportSection(
            section_id="audit",
            title="Model review",
            statements=[f"{finding.title}: {finding.detail}" for finding in run.audit_findings],
            data_references=["audit_findings"],
        ),
        ReportSection(
            section_id="scope",
            title="Scope and limitations",
            statements=run.limitations,
            data_references=["limitations", "manifest"],
        ),
    ]
    if report_type == "technical":
        common.insert(1, ReportSection(
            section_id="method",
            title="Methods and reproducibility",
            statements=[
                f"Code version: {run.manifest.code_version}.",
                f"Random seed: {run.manifest.random_seed}; model IDs: {run.manifest.model_ids}.",
                f"Analysis resolution: {run.resolution.analysis_resolution}; hazard resolution: {run.resolution.hazard_resolution}.",
            ],
            data_references=["manifest", "resolution", "assumptions"],
        ))
    elif report_type == "underwriting":
        common.insert(1, ReportSection(
            section_id="financial",
            title="Financial view",
            statements=[
                f"Gross insured median: {money(run.gross_distribution.p50_usd)}.",
                f"Net insured median: {money(run.net_insured_distribution.p50_usd)}.",
                f"Terms: deductible ${run.financial_terms.deductible_usd:,.0f}, limit {run.financial_terms.limit_usd}, coinsurance {run.financial_terms.coinsurance:.0%}.",
            ],
            data_references=["financial_terms", "gross_distribution", "net_insured_distribution"],
        ))
    elif report_type == "public":
        common[0].statements = [
            "This demonstration estimates a range of possible economic loss for a synthetic flood scenario.",
            "It is not a property appraisal, insurance quote, official warning, or prediction of what will happen.",
        ]

    return StructuredRunReport(
        report_id=f"report-{uuid.uuid4().hex[:12]}",
        run_id=run.run_id,
        report_type=report_type,
        generated_at=datetime.now(timezone.utc),
        title=f"{run.scenario_label} - {report_type.title()} report",
        sections=common,
        citations=run.sources,
        manifest=run.manifest,
        limitations=run.limitations,
    )


def data_coverage() -> list[DataCoverageItem]:
    return [
        DataCoverageItem(
            layer_id="hazard-depth",
            label="Flood depth at structure",
            availability="available_demo",
            use_in_run="Hazard intensity input",
            source="Synthetic RiskChain demonstration surface",
            geographic_resolution="~10 m labelled demonstration grid",
            temporal_resolution="Single 100-year demonstration event",
            attribute_origin=AttributeOrigin.MODEL_INFERRED,
            limitations=["Not FEMA NFHL", "Not a hydraulic simulation", "Not surveyed depth"],
        ),
        DataCoverageItem(
            layer_id="building-exposure",
            label="Demonstration buildings",
            availability="available_demo",
            use_in_run="Geometry and exposure attributes",
            source="RiskChain demonstration exposure",
            geographic_resolution="Selected point assets",
            temporal_resolution="Static snapshot",
            attribute_origin=AttributeOrigin.MODEL_INFERRED,
            limitations=["Not a complete building inventory", "Values and attributes are synthetic"],
        ),
        DataCoverageItem(
            layer_id="population",
            label="Population exposure",
            availability="unavailable",
            use_in_run="Not used",
            source="No population dataset connected to the CAT run",
            geographic_resolution="Unavailable",
            temporal_resolution="Unavailable",
            attribute_origin=AttributeOrigin.MISSING,
            limitations=["The run must not claim people affected"],
        ),
        DataCoverageItem(
            layer_id="claims",
            label="Insurance claims",
            availability="unavailable",
            use_in_run="Not used",
            source="No licensed claims dataset connected",
            geographic_resolution="Unavailable",
            temporal_resolution="Unavailable",
            attribute_origin=AttributeOrigin.MISSING,
            limitations=["No model calibration or post-event validation from claims"],
        ),
    ]


def capability_coverage() -> CapabilityCoverage:
    """Truthful implementation audit of the 16 requested deliverables."""

    rows = [
        ("1. Assumptions", "implemented", ["PRD assumptions", "run assumptions and manifests"], None),
        ("2. Product requirements", "implemented", ["docs/PRD.md", "documented non-goals and personas"], None),
        ("3. Information architecture", "partial", ["working app routes and navigation"], "Target RiskChain IA is broader than the current MVP routes."),
        ("4. Detailed wireframes", "partial", ["implemented map-first interface"], "Nine requested screens are not all represented as formal wireframes."),
        ("5. User journeys", "partial", ["flood, live-event and portfolio paths work"], "Full researcher and underwriter journeys need dedicated UI."),
        ("6. Data-source matrix", "partial", ["typed source registry and health checks"], "Product-level licences and fallbacks still require periodic legal review."),
        ("7. Scientific model specification", "implemented", ["docs/CAT_MODEL_SPEC.md", "scientific-behaviour tests"], None),
        ("8. System architecture", "implemented", ["docs/ARCHITECTURE.md", "modular FastAPI services"], None),
        ("9. Database and API design", "partial", ["typed API and PostGIS migration design"], "Production persistence still uses an in-process demonstration repository."),
        ("10. AI architecture", "partial", ["grounded assistant, tool trace and Groq prose guard"], "Provider abstraction, retrieval and evaluation registry are not complete."),
        ("11. Frontend component tree", "partial", ["reusable map, panel, trust and chart components"], "No generated component catalogue is exposed yet."),
        ("12. MVP code scaffold", "implemented", ["Next.js map workspace", "FastAPI adapters and typed error states"], None),
        ("13. Bethlehem demo scenario", "implemented", ["flood CAT run", "uncertainty, cascade, mitigation and report APIs"], None),
        ("14. Test plan", "implemented", ["docs/TEST_PLAN.md", "software and scientific behaviour tests"], None),
        ("15. Deployment plan", "implemented", ["docs/DEPLOYMENT.md", "Vercel and container configurations"], None),
        ("16. Product roadmap", "partial", ["phased PRD roadmap"], "Commercial milestones need owners, budgets and acceptance gates."),
    ]
    capabilities = [
        CapabilityStatus(deliverable=name, status=status, evidence=evidence, next_gap=gap)
        for name, status, evidence, gap in rows
    ]
    counts = {status: sum(1 for item in capabilities if item.status == status) for status in ("implemented", "partial", "not_started")}
    return CapabilityCoverage(
        implemented=counts["implemented"],
        partial=counts["partial"],
        not_started=counts["not_started"],
        total=len(capabilities),
        capabilities=capabilities,
    )
