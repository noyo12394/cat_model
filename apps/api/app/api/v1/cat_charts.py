"""Chart-data API: drawable series derived from immutable model runs.

Kept in its own router (same ``/cat`` prefix) so the chart surface can evolve
without touching the core model-run contracts in ``catmodel.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import repo_dep
from app.db.memory_repository import MemoryRepository
from app.schemas.catmodel import CatModelRunResult
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

router = APIRouter(prefix="/cat", tags=["cat-charts"])


def _load_run(repo: MemoryRepository, run_id: str) -> CatModelRunResult:
    run = repo.get_cat_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Model run not found")
    assert isinstance(run, CatModelRunResult)
    return run


@router.get("/charts/fragility/{function_id}", response_model=FragilityChart)
def get_fragility_chart(function_id: str) -> FragilityChart:
    """Depth-damage curve for one approved vulnerability function."""
    chart = fragility_chart(function_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Vulnerability function not found")
    return chart


@router.get("/model-runs/{run_id}/charts/fragility", response_model=FragilityChart)
def get_run_fragility_chart(
    run_id: str,
    asset_id: str = Query(..., min_length=1),
    repo: MemoryRepository = Depends(repo_dep),
) -> FragilityChart:
    """The asset's curve with its own depth/damage point marked."""
    run = _load_run(repo, run_id)
    chart = fragility_chart_for_asset(run, asset_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Asset not found in this run")
    return chart


@router.get("/model-runs/{run_id}/charts/loss-histogram", response_model=LossHistogram)
def get_loss_histogram(
    run_id: str,
    bins: int = Query(default=24, ge=5, le=60),
    repo: MemoryRepository = Depends(repo_dep),
) -> LossHistogram:
    return loss_histogram(_load_run(repo, run_id), bins=bins)


@router.get("/model-runs/{run_id}/charts/ep", response_model=EPCurveChart)
def get_ep_chart(
    run_id: str,
    years: int = Query(default=5000, ge=1000, le=20000),
    seed: int = 7,
    repo: MemoryRepository = Depends(repo_dep),
) -> EPCurveChart:
    return ep_chart(_load_run(repo, run_id), years=years, seed=seed)


@router.get("/model-runs/{run_id}/charts/waterfall", response_model=LossWaterfall)
def get_loss_waterfall(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> LossWaterfall:
    return loss_waterfall(_load_run(repo, run_id))


@router.get("/model-runs/{run_id}/charts/drivers", response_model=LossDrivers)
def get_loss_drivers(
    run_id: str,
    top: int = Query(default=10, ge=1, le=50),
    repo: MemoryRepository = Depends(repo_dep),
) -> LossDrivers:
    return loss_drivers(_load_run(repo, run_id), top=top)


@router.get("/model-runs/{run_id}/charts/water-rise", response_model=WaterRiseSweep)
def get_water_rise_sweep(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> WaterRiseSweep:
    """Loss vs water-level offset - powers an animated 'raise the water' slider."""
    return water_rise_sweep(_load_run(repo, run_id))
