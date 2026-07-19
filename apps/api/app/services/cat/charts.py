"""Chart-data derivations for the frontend (make the results *drawable*).

Everything here is computed from an immutable stored run plus the approved
model library - the same deterministic code paths as the run itself, never a
language model. The point is that the frontend should only have to draw:

* fragility/depth-damage curve with the asset's own point marked,
* Monte Carlo loss histogram (consistent with the run's stored percentiles),
* OEP/AEP exceedance series,
* loss waterfall (ground-up -> deductible -> limit -> coinsurance -> net),
* ranked loss drivers with cumulative share, and
* a water-rise sweep (total loss as the water level moves), which powers an
  animated "raise the water" slider in the UI.

The demo run always uses the fixed demonstration exposure, so charts that need
asset detail reconstruct it from the same seeded builder the run used; each
payload's ``basis`` states exactly that.
"""

from __future__ import annotations

from app.data.demo.lehigh_valley_exposure import (
    DEMO_FLOOD_DEPTH_100YR_FT,
    build_demo_exposure,
)
from app.schemas.catmodel import CatModelRunResult, ExposureAsset
from app.schemas.charts import (
    ChartAxis,
    EPCurveChart,
    EPSeries,
    FragilityChart,
    HistogramBin,
    LossDriver,
    LossDrivers,
    LossHistogram,
    LossWaterfall,
    WaterfallStep,
    WaterRisePoint,
    WaterRiseSweep,
    XYPoint,
)
from app.services.cat.damage import compute_asset_damage
from app.services.cat.probabilistic import demo_flood_event_set, run_event_set
from app.services.cat.uncertainty import AssetLossSpec, portfolio_ground_up_samples
from app.services.cat.vulnerability import (
    VULNERABILITY_FUNCTIONS,
    mean_damage_ratio,
    select_function,
)

_DEPTH_AXIS = ChartAxis(label="Flood depth above first floor", unit="ft")
_RATIO_AXIS = ChartAxis(label="Mean structural damage ratio", unit="ratio 0-1")
_LOSS_AXIS = ChartAxis(label="Portfolio ground-up loss", unit="USD")

_DEMO_BASIS = (
    "Derived from the run's demonstration exposure and approved experimental "
    "curves; demonstration output, not observed conditions."
)


def _demo_assets() -> tuple[list[ExposureAsset], dict[str, float]]:
    return build_demo_exposure(), DEMO_FLOOD_DEPTH_100YR_FT


def _asset_by_id(asset_id: str) -> ExposureAsset | None:
    return next((a for a in build_demo_exposure() if a.asset_id == asset_id), None)


def fragility_chart(function_id: str, asset_id: str | None = None, run: CatModelRunResult | None = None) -> FragilityChart | None:
    vfunc = VULNERABILITY_FUNCTIONS.get(function_id)
    if vfunc is None:
        return None

    marker = marker_asset = None
    marker_extrapolated = None
    state_probs = None
    if asset_id and run is not None:
        dmg = next((d for d in run.asset_damage if d.asset_id == asset_id), None)
        if dmg is not None:
            marker = XYPoint(x=dmg.intensity, y=dmg.mean_damage_ratio)
            marker_asset = asset_id
            marker_extrapolated = dmg.extrapolated
            state_probs = dmg.damage_state_probabilities

    return FragilityChart(
        function_id=vfunc.function_id,
        title=vfunc.name,
        x_axis=_DEPTH_AXIS,
        y_axis=_RATIO_AXIS,
        curve=[XYPoint(x=p.intensity, y=p.mean_damage_ratio) for p in vfunc.curve],
        calibration_min=vfunc.calibration_min,
        calibration_max=vfunc.calibration_max,
        approval_status=vfunc.approval_status.value,
        marker=marker,
        marker_asset_id=marker_asset,
        marker_extrapolated=marker_extrapolated,
        damage_state_probabilities=state_probs,
        note=vfunc.applicability_notes,
    )


def fragility_chart_for_asset(run: CatModelRunResult, asset_id: str) -> FragilityChart | None:
    dmg = next((d for d in run.asset_damage if d.asset_id == asset_id), None)
    if dmg is None:
        return None
    return fragility_chart(dmg.vulnerability_function_id, asset_id=asset_id, run=run)


def _specs_for_run(run: CatModelRunResult) -> list[AssetLossSpec]:
    assets, _ = _demo_assets()
    by_id = {a.asset_id: a for a in assets}
    specs: list[AssetLossSpec] = []
    for dmg in run.asset_damage:
        asset = by_id.get(dmg.asset_id)
        if asset is None:
            continue
        vfunc = select_function(asset.occupancy)
        specs.append(AssetLossSpec(
            asset_id=asset.asset_id,
            replacement_value_usd=asset.replacement_value_usd,
            contents_value_usd=asset.contents_value_usd,
            business_interruption_daily_usd=asset.business_interruption_daily_usd,
            mean_building_ratio=dmg.mean_damage_ratio,
            cov=vfunc.damage_ratio_cov,
            terms=run.financial_terms,
        ))
    return specs


def loss_histogram(run: CatModelRunResult, bins: int = 24) -> LossHistogram:
    seed = run.manifest.random_seed
    iterations = int(run.manifest.parameters.get("iterations", 2000))
    samples = portfolio_ground_up_samples(_specs_for_run(run), seed=seed, iterations=iterations)

    low, high = min(samples), max(samples)
    span = max(high - low, 1.0)
    width = span / bins
    counts = [0] * bins
    for value in samples:
        idx = min(bins - 1, int((value - low) / width))
        counts[idx] += 1

    dist = run.ground_up_distribution
    return LossHistogram(
        run_id=run.run_id,
        title="Monte Carlo ground-up loss distribution",
        x_axis=_LOSS_AXIS,
        y_axis=ChartAxis(label="Simulations", unit="count"),
        bins=[HistogramBin(lower=round(low + i * width, 2), upper=round(low + (i + 1) * width, 2), count=c)
              for i, c in enumerate(counts)],
        samples=len(samples),
        p10_usd=dist.p10_usd,
        p50_usd=dist.p50_usd,
        p90_usd=dist.p90_usd,
        basis=f"Re-sampled with the run's seed {seed} and {iterations} iterations; consistent with its stored percentiles. {_DEMO_BASIS}",
    )


def ep_chart(run: CatModelRunResult, years: int = 5000, seed: int = 7) -> EPCurveChart:
    prob = run_event_set(demo_flood_event_set(run.ground_up_distribution.p50_usd), seed=seed, years=years)
    return EPCurveChart(
        run_id=run.run_id,
        title="Exceedance-probability curves",
        x_axis=ChartAxis(label="Loss return period", unit="years"),
        y_axis=ChartAxis(label="Annual loss", unit="USD"),
        series=[
            EPSeries(name="OEP", points=[XYPoint(x=p.return_period_years, y=p.loss_usd) for p in prob.oep_curve]),
            EPSeries(name="AEP", points=[XYPoint(x=p.return_period_years, y=p.loss_usd) for p in prob.aep_curve]),
        ],
        aal_usd=prob.aal_usd,
        basis=prob.method,
        caveat="Loss return periods are quantiles of simulated loss, not hazard-event return periods.",
    )


def loss_waterfall(run: CatModelRunResult) -> LossWaterfall:
    ground_up = sum(f.ground_up_loss_usd for f in run.asset_financial)
    deductible = sum(f.deductible_applied_usd for f in run.asset_financial)
    gross = sum(f.gross_loss_usd for f in run.asset_financial)
    net = sum(f.net_insured_loss_usd for f in run.asset_financial)
    over_limit = max(0.0, ground_up - deductible - gross)
    coinsurance_retained = max(0.0, gross - net)

    steps: list[WaterfallStep] = []
    running = ground_up
    steps.append(WaterfallStep(label="Ground-up loss", amount_usd=round(ground_up, 2), running_total_usd=round(running, 2)))
    for label, reduction in (
        ("Deductible retained by insured", deductible),
        ("Above policy limit (uninsured)", over_limit),
        ("Coinsurance share retained", coinsurance_retained),
    ):
        running -= reduction
        steps.append(WaterfallStep(label=label, amount_usd=round(-reduction, 2), running_total_usd=round(running, 2)))
    steps.append(WaterfallStep(label="Net insured loss", amount_usd=round(net, 2), running_total_usd=round(net, 2)))

    return LossWaterfall(
        run_id=run.run_id,
        title="From economic loss to insured loss",
        steps=steps,
        currency=run.financial_terms.currency,
        basis=f"Deterministic asset-level expected losses (not the Monte Carlo median). {_DEMO_BASIS}",
    )


def loss_drivers(run: CatModelRunResult, top: int = 10) -> LossDrivers:
    assets, _ = _demo_assets()
    names = {a.asset_id: a.name for a in assets}
    total = sum(d.ground_up_loss_usd for d in run.asset_damage) or 1.0
    ranked = sorted(run.asset_damage, key=lambda d: d.ground_up_loss_usd, reverse=True)[:top]

    drivers: list[LossDriver] = []
    cumulative = 0.0
    for dmg in ranked:
        share = dmg.ground_up_loss_usd / total
        cumulative += share
        drivers.append(LossDriver(
            asset_id=dmg.asset_id,
            name=names.get(dmg.asset_id, dmg.asset_id),
            ground_up_loss_usd=dmg.ground_up_loss_usd,
            share=round(share, 4),
            cumulative_share=round(min(1.0, cumulative), 4),
            depth_ft=dmg.intensity,
            damage_ratio=dmg.mean_damage_ratio,
            extrapolated=dmg.extrapolated,
        ))

    return LossDrivers(
        run_id=run.run_id,
        title="Largest loss contributors",
        total_ground_up_usd=round(total, 2),
        drivers=drivers,
        basis=_DEMO_BASIS,
    )


def water_rise_sweep(run: CatModelRunResult, low_ft: float = -4.0, high_ft: float = 8.0, step_ft: float = 0.5) -> WaterRiseSweep:
    assets, depths = _demo_assets()
    points: list[WaterRisePoint] = []
    offset = low_ft
    while offset <= high_ft + 1e-9:
        total = 0.0
        wet = 0
        for asset in assets:
            depth = depths.get(asset.asset_id, 0.0) + offset
            vfunc = select_function(asset.occupancy)
            ratio, _ = mean_damage_ratio(depth, vfunc)
            if ratio > 0.0:
                wet += 1
            total += compute_asset_damage(asset, depth, vfunc).ground_up_loss_usd
        points.append(WaterRisePoint(offset_ft=round(offset, 2), total_ground_up_usd=round(total, 2), assets_wet=wet))
        offset += step_ft

    return WaterRiseSweep(
        run_id=run.run_id,
        title="Loss as the water level changes",
        x_axis=ChartAxis(label="Water level relative to modelled scenario", unit="ft"),
        y_axis=_LOSS_AXIS,
        points=points,
        scenario_offset_ft=0.0,
        basis=f"Mean damage ratio per asset at each shifted depth; same curves as the run. {_DEMO_BASIS}",
        caveat=(
            "A uniform water-level shift is a visual sensitivity sweep, not a hydraulic model - "
            "real floods do not rise uniformly across a valley."
        ),
    )
