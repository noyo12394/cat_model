"""Model auditor (section 26).

After a run, automatically surface data-quality, calibration and double-counting
concerns as a structured review card. The auditor never silently fixes anything;
it recommends actions for a human reviewer.
"""

from __future__ import annotations

from app.schemas.catmodel import (
    AssetDamageResult,
    AttributeOrigin,
    ExposureAsset,
    ModelAuditFinding,
    VulnerabilityFunction,
)

# Attribute origins that are not directly observed/measured.
_INFERRED_ORIGINS = {
    AttributeOrigin.MODEL_INFERRED,
    AttributeOrigin.DEFAULT_ASSUMPTION,
    AttributeOrigin.MISSING,
}


def audit_run(
    assets: list[ExposureAsset],
    damages: list[AssetDamageResult],
    vfunc_by_asset: dict[str, VulnerabilityFunction],
    hazard_resolution_m: float,
    analysis_resolution_label: str,
) -> list[ModelAuditFinding]:
    findings: list[ModelAuditFinding] = []
    n = len(assets) or 1

    # Inferred construction/occupancy share.
    inferred_construction = sum(
        1 for a in assets if a.attribute_origins.get("construction") in _INFERRED_ORIGINS
    )
    if inferred_construction:
        pct = round(100 * inferred_construction / n)
        findings.append(ModelAuditFinding(
            code="inferred_construction",
            severity="warning" if pct >= 25 else "info",
            title="Inferred construction classes",
            detail=f"{pct}% of assets use an inferred or default construction class.",
            recommendation="Confirm construction from assessor or survey data before underwriting use.",
        ))

    # Missing first-floor elevation - the classic flood loss driver.
    missing_ffe = sum(
        1 for a in assets
        if a.attribute_origins.get("first_floor_elevation_ft") == AttributeOrigin.MISSING
        or a.first_floor_elevation_ft is None
    )
    if missing_ffe:
        pct = round(100 * missing_ffe / n)
        findings.append(ModelAuditFinding(
            code="missing_first_floor_elevation",
            severity="high" if pct >= 50 else "warning",
            title="Missing first-floor elevation",
            detail=f"{pct}% of assets have no first-floor elevation; this is often the largest flood-loss driver.",
            recommendation="Obtain elevation certificates or lidar-derived first-floor heights.",
        ))

    # Business interruption included?
    bi_included = any(d.business_interruption_loss_usd > 0 for d in damages)
    if not bi_included:
        findings.append(ModelAuditFinding(
            code="bi_excluded",
            severity="info",
            title="Business interruption not contributing",
            detail="No business-interruption loss is present in this run.",
            recommendation="Confirm whether BI values are intentionally zero for these occupancies.",
        ))

    # Extrapolation beyond calibration range.
    extrapolated = [d.asset_id for d in damages if d.extrapolated]
    if extrapolated:
        findings.append(ModelAuditFinding(
            code="calibration_extrapolation",
            severity="warning",
            title="Vulnerability extrapolated beyond calibration range",
            detail=f"{len(extrapolated)} asset(s) have a hazard intensity outside the curve's calibration range.",
            recommendation="Treat those asset losses as low-confidence; seek a curve valid at these depths.",
        ))

    # Occupancy vs curve asset-class mismatch.
    mismatches = [
        a.asset_id for a in assets
        if (vf := vfunc_by_asset.get(a.asset_id)) and vf.asset_class != a.occupancy
        and not (a.occupancy == "commercial" and vf.asset_class == "commercial")
    ]
    if mismatches:
        findings.append(ModelAuditFinding(
            code="asset_class_mismatch",
            severity="info",
            title="Occupancy mapped to a nearest-available curve",
            detail=f"{len(mismatches)} asset(s) were mapped to a vulnerability curve for a related occupancy.",
            recommendation="Add occupancy-specific curves where available.",
        ))

    # Resolution mismatch: hazard coarser than the analysis unit.
    if hazard_resolution_m >= 10 and "building" in analysis_resolution_label.lower():
        findings.append(ModelAuditFinding(
            code="resolution_mismatch",
            severity="warning",
            title="Hazard coarser than analysis unit",
            detail=f"Hazard resolution is ~{hazard_resolution_m:g} m while analysis is at {analysis_resolution_label}.",
            recommendation="Do not over-interpret single-building results from a coarser hazard grid.",
        ))

    return findings
