"""Chart-data API: drawable series derived from a model run.

Serverless-safe by design. The public deployment is a stateless function whose
in-memory run store is not shared across invocations, so a chart request that
arrives on a fresh instance would not find a run saved by an earlier POST. To
avoid the panels locking, every endpoint falls back to **recomputing the
deterministic demo run** from the run's defining parameters (seed + financial
terms + iterations) when the run id is not in memory. The demo run is fully
reproducible, so a recomputed run yields identical charts.

Kept in its own router (same ``/cat`` prefix) so the chart surface can evolve
without touching the core model-run contracts in ``catmodel.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import repo_dep
from app.data.demo.lehigh_valley_exposure import (
    DEMO_FLOOD_DEPTH_100YR_FT,
    build_demo_exposure,
)
from app.db.memory_repository import MemoryRepository
from app.schemas.catmodel import CatModelRunResult, FinancialTerms
from app.schemas.charts import (
    EPCurveChart,
    FragilityChart,
    LossDrivers,
    LossHistogram,
    LossWaterfall,
    WaterRiseSweep,
)
from app.services.cat.charts import (
    ep_chart,
    fragility_chart,
    fragility_chart_for_asset,
    loss_drivers,
    loss_histogram,
    loss_waterfall,
    water_rise_sweep,
)
from app.services.cat.run import run_flood_scenario

router = APIRouter(prefix="/cat", tags=["cat-charts"])

REGION_LABEL = "Bethlehem / Lehigh Valley, PA (demonstration)"


def _resolve_run(
    repo: MemoryRepository,
    run_id: str,
    *,
    seed: int,
    deductible_usd: float,
    limit_usd: float | None,
    coinsurance: float,
    iterations: int,
) -> CatModelRunResult:
    """Return the stored run, or recompute the deterministic demo run.

    Recomputation makes charts work on a cold serverless instance that never
    saw the original POST. Because the demo exposure/depths are fixed and the
    seed + terms are supplied, the recomputed run is identical to the one the
    client is displaying.
    """
    stored = repo.get_cat_run(run_id)
    if isinstance(stored, CatModelRunResult):
        return stored
    terms = FinancialTerms(
        deductible_usd=max(0.0, deductible_usd),
        limit_usd=(None if limit_usd in (None, 0) else max(0.0, limit_usd)),
        coinsurance=min(1.0, max(0.0, coinsurance)),
    )
    return run_flood_scenario(
        build_demo_exposure(), DEMO_FLOOD_DEPTH_100YR_FT, terms,
        scenario_label="100-year flood (demonstration)", region_label=REGION_LABEL,
        seed=seed, iterations=iterations,
    )


# Shared run-parameter query args (all optional; defaults reproduce the standard run).
def _run_params(
    seed: int = Query(default=12345),
    deductible_usd: float = Query(default=0.0, ge=0.0),
    limit_usd: float | None = Query(default=None, ge=0.0),
    coinsurance: float = Query(default=1.0, ge=0.0, le=1.0),
    iterations: int = Query(default=2000, ge=200, le=5000),
) -> dict:
    return {"seed": seed, "deductible_usd": deductible_usd, "limit_usd": limit_usd,
            "coinsurance": coinsurance, "iterations": iterations}


@router.get("/charts/fragility/{function_id}", response_model=FragilityChart)
def get_fragility_chart(function_id: str) -> FragilityChart:
    """Depth-damage curve for one approved vulnerability function (stateless)."""
    chart = fragility_chart(function_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Vulnerability function not found")
    return chart


@router.get("/model-runs/{run_id}/charts/fragility", response_model=FragilityChart)
def get_run_fragility_chart(
    run_id: str,
    asset_id: str = Query(..., min_length=1),
    params: dict = Depends(_run_params),
    repo: MemoryRepository = Depends(repo_dep),
) -> FragilityChart:
    """The asset's curve with its own depth/damage point marked."""
    run = _resolve_run(repo, run_id, **params)
    chart = fragility_chart_for_asset(run, asset_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Asset not found in this run")
    return chart


@router.get("/model-runs/{run_id}/charts/loss-histogram", response_model=LossHistogram)
def get_loss_histogram(
    run_id: str,
    bins: int = Query(default=24, ge=5, le=60),
    params: dict = Depends(_run_params),
    repo: MemoryRepository = Depends(repo_dep),
) -> LossHistogram:
    return loss_histogram(_resolve_run(repo, run_id, **params), bins=bins)


@router.get("/model-runs/{run_id}/charts/ep", response_model=EPCurveChart)
def get_ep_chart(
    run_id: str,
    years: int = Query(default=5000, ge=1000, le=20000),
    ep_seed: int = 7,
    params: dict = Depends(_run_params),
    repo: MemoryRepository = Depends(repo_dep),
) -> EPCurveChart:
    return ep_chart(_resolve_run(repo, run_id, **params), years=years, seed=ep_seed)


@router.get("/model-runs/{run_id}/charts/waterfall", response_model=LossWaterfall)
def get_loss_waterfall(
    run_id: str,
    params: dict = Depends(_run_params),
    repo: MemoryRepository = Depends(repo_dep),
) -> LossWaterfall:
    return loss_waterfall(_resolve_run(repo, run_id, **params))


@router.get("/model-runs/{run_id}/charts/drivers", response_model=LossDrivers)
def get_loss_drivers(
    run_id: str,
    top: int = Query(default=10, ge=1, le=50),
    params: dict = Depends(_run_params),
    repo: MemoryRepository = Depends(repo_dep),
) -> LossDrivers:
    return loss_drivers(_resolve_run(repo, run_id, **params), top=top)


@router.get("/model-runs/{run_id}/charts/water-rise", response_model=WaterRiseSweep)
def get_water_rise_sweep(
    run_id: str,
    params: dict = Depends(_run_params),
    repo: MemoryRepository = Depends(repo_dep),
) -> WaterRiseSweep:
    """Loss vs water-level offset - powers an animated 'raise the water' slider."""
    return water_rise_sweep(_resolve_run(repo, run_id, **params))
