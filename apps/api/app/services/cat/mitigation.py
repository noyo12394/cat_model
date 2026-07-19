"""Mitigation sandbox (section 17).

Each intervention is evaluated by re-running the deterministic scenario with the
intervention's *modelled* effect applied, then comparing aggregate ground-up
loss. A risk reduction is only claimed when an approved model supports the
mechanism (rule: do not claim causal reduction otherwise). Backup power, for
instance, reduces business-interruption downtime, not structural flood damage.
"""

from __future__ import annotations

from app.schemas.catmodel import ExposureAsset, MitigationOption, MitigationResult
from app.schemas.enums import Confidence
from app.services.cat.damage import contents_damage_ratio, downtime_days
from app.services.cat.vulnerability import mean_damage_ratio, select_function

MITIGATION_OPTIONS: dict[str, MitigationOption] = {
    "mit-elevate-2ft": MitigationOption(
        option_id="mit-elevate-2ft",
        name="Elevate lowest floor by 2 ft",
        description="Raise the first-floor elevation of residential structures by 2 feet.",
        cost_usd=45_000,
        applies_to_occupancy=["residential"],
        mechanism="Reduces effective flood depth at structure by 2 ft via the depth-damage curve.",
        supported_by_model=True,
    ),
    "mit-floodproof-3ft": MitigationOption(
        option_id="mit-floodproof-3ft",
        name="Dry floodproofing to 3 ft",
        description="Seal and protect commercial/industrial ground floors up to 3 ft.",
        cost_usd=120_000,
        applies_to_occupancy=["commercial", "industrial"],
        mechanism="Reduces the structural damage ratio by 60% where depth is at or below 3 ft.",
        supported_by_model=True,
    ),
    "mit-backup-power": MitigationOption(
        option_id="mit-backup-power",
        name="Add backup power",
        description="Standby generation for critical and commercial facilities.",
        cost_usd=250_000,
        applies_to_occupancy=["hospital", "commercial"],
        mechanism="Reduces business-interruption downtime by 40%; does not reduce structural flood damage.",
        supported_by_model=True,
    ),
}

_FLOODPROOF_DEPTH_LIMIT = 3.0
_FLOODPROOF_EFFECTIVENESS = 0.60
_ELEVATION_FT = 2.0
_BACKUP_BI_REDUCTION = 0.40


def _asset_ground_up(
    asset: ExposureAsset,
    depth_ft: float,
    *,
    depth_delta: float = 0.0,
    ratio_factor: float = 1.0,
    downtime_factor: float = 1.0,
) -> float:
    vf = select_function(asset.occupancy)
    effective_depth = depth_ft - depth_delta
    b_ratio, _ = mean_damage_ratio(effective_depth, vf)
    b_ratio = max(0.0, b_ratio * ratio_factor)
    c_ratio = contents_damage_ratio(b_ratio)
    dt = downtime_days(b_ratio) * downtime_factor
    return (
        asset.replacement_value_usd * b_ratio
        + asset.contents_value_usd * c_ratio
        + asset.business_interruption_daily_usd * dt
    )


def _mitigated_ground_up(option: MitigationOption, asset: ExposureAsset, depth_ft: float) -> float:
    if asset.occupancy not in option.applies_to_occupancy:
        return _asset_ground_up(asset, depth_ft)
    if option.option_id == "mit-elevate-2ft":
        return _asset_ground_up(asset, depth_ft, depth_delta=_ELEVATION_FT)
    if option.option_id == "mit-floodproof-3ft":
        factor = 1.0 - _FLOODPROOF_EFFECTIVENESS if depth_ft <= _FLOODPROOF_DEPTH_LIMIT else 1.0
        return _asset_ground_up(asset, depth_ft, ratio_factor=factor)
    if option.option_id == "mit-backup-power":
        return _asset_ground_up(asset, depth_ft, downtime_factor=1.0 - _BACKUP_BI_REDUCTION)
    return _asset_ground_up(asset, depth_ft)


def evaluate_mitigation(
    option: MitigationOption,
    assets: list[ExposureAsset],
    depths: dict[str, float],
) -> MitigationResult:
    baseline = sum(_asset_ground_up(a, depths.get(a.asset_id, 0.0)) for a in assets)
    mitigated = sum(_mitigated_ground_up(option, a, depths.get(a.asset_id, 0.0)) for a in assets)
    avoided = max(0.0, baseline - mitigated)

    applicable = [a for a in assets if a.occupancy in option.applies_to_occupancy]
    total_cost = option.cost_usd * len(applicable)
    bcr = round(avoided / total_cost, 2) if total_cost > 0 else None

    return MitigationResult(
        option_id=option.option_id,
        name=option.name,
        baseline_median_usd=round(baseline, 2),
        with_mitigation_median_usd=round(mitigated, 2),
        avoided_loss_usd=round(avoided, 2),
        cost_usd=round(total_cost, 2),
        benefit_cost_ratio=bcr,
        confidence=Confidence.LOW if not option.supported_by_model else Confidence.MODERATE,
        assumptions=[
            f"Applied to {len(applicable)} asset(s) of occupancy {option.applies_to_occupancy}.",
            option.mechanism,
            "Cost is a demonstration per-asset figure multiplied by the number of applicable assets.",
        ],
        caveat=(
            "Avoided loss is for THIS single modelled scenario (ground-up). A full benefit-cost "
            "ratio should use avoided average annual loss over the asset's life, not one event."
        ),
    )
