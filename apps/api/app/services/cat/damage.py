"""Damage module (section 10.4): asset-level physical loss.

Building, contents and business-interruption losses use *different* damage
relationships (the master prompt explicitly forbids assuming one function for
all three). Contents are assumed slightly more depth-sensitive than structure at
low depths; downtime scales with structural damage. All multipliers are
demonstration assumptions and are surfaced as such in the run's assumptions.
"""

from __future__ import annotations

from app.schemas.catmodel import AssetDamageResult, ExposureAsset, VulnerabilityFunction
from app.services.cat.vulnerability import (
    damage_state_probabilities,
    mean_damage_ratio,
)

# Demonstration relationships between structural damage ratio and the other two
# loss components. Documented as assumptions, not fitted parameters.
CONTENTS_MULTIPLIER = 1.15  # contents damage ratio relative to structure, capped at 1.0
MAX_DOWNTIME_DAYS = 180.0  # downtime at complete structural loss


def contents_damage_ratio(building_ratio: float) -> float:
    return min(1.0, building_ratio * CONTENTS_MULTIPLIER)


def downtime_days(building_ratio: float) -> float:
    """Downtime scales with structural damage ratio up to a cap."""
    return round(MAX_DOWNTIME_DAYS * building_ratio, 1)


def compute_asset_damage(
    asset: ExposureAsset,
    depth_ft: float,
    vfunc: VulnerabilityFunction,
) -> AssetDamageResult:
    building_ratio, extrapolated = mean_damage_ratio(depth_ft, vfunc)
    contents_ratio = contents_damage_ratio(building_ratio)
    dt_days = downtime_days(building_ratio)

    building_loss = asset.replacement_value_usd * building_ratio
    contents_loss = asset.contents_value_usd * contents_ratio
    bi_loss = asset.business_interruption_daily_usd * dt_days
    ground_up = building_loss + contents_loss + bi_loss

    return AssetDamageResult(
        asset_id=asset.asset_id,
        intensity=depth_ft,
        mean_damage_ratio=round(building_ratio, 4),
        damage_state_probabilities=damage_state_probabilities(building_ratio),
        building_loss_usd=round(building_loss, 2),
        contents_loss_usd=round(contents_loss, 2),
        business_interruption_loss_usd=round(bi_loss, 2),
        ground_up_loss_usd=round(ground_up, 2),
        extrapolated=extrapolated,
        vulnerability_function_id=vfunc.function_id,
    )
