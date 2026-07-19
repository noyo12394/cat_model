"""RiskChain catastrophe-model API (sections 22, 24).

Long calculations here are deterministic and fast enough to run inline; each
returns a full, immutable run result with a manifest. A production build would
move these behind the job-queue pattern (return a job id + status), which these
contracts are shaped to allow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import repo_dep
from app.data.demo.lehigh_valley_exposure import (
    DEMO_FLOOD_DEPTH_100YR_FT,
    build_demo_exposure,
)
from app.db.memory_repository import MemoryRepository
from app.schemas.catmodel import (
    CatModelRunResult,
    ExposureAsset,
    FinancialTerms,
    MitigationOption,
    MitigationResult,
    ModelRegistryEntry,
    ProbabilisticResult,
    VulnerabilityFunction,
)
from app.services.cat.mitigation import MITIGATION_OPTIONS, evaluate_mitigation
from app.services.cat.model_registry import get_model, list_models
from app.services.cat.probabilistic import demo_flood_event_set, run_event_set
from app.services.cat.run import run_flood_scenario
from app.services.cat.vulnerability import VULNERABILITY_FUNCTIONS

router = APIRouter(prefix="/cat", tags=["cat-model"])

REGION_LABEL = "Bethlehem / Lehigh Valley, PA (demonstration)"


class RunRequest(BaseModel):
    scenario_label: str = "100-year flood (demonstration)"
    deductible_usd: float = Field(default=0.0, ge=0.0)
    limit_usd: float | None = Field(default=None, ge=0.0)
    coinsurance: float = Field(default=1.0, ge=0.0, le=1.0)
    seed: int = 12345
    iterations: int = Field(default=2000, ge=200, le=5000)
    parent_run_id: str | None = None


class RunSummary(BaseModel):
    run_id: str
    scenario_label: str
    ground_up_p50_usd: float
    gross_p50_usd: float
    confidence: str


def _demo_assets_and_depths() -> tuple[list[ExposureAsset], dict[str, float]]:
    return build_demo_exposure(), DEMO_FLOOD_DEPTH_100YR_FT


@router.get("/exposure/demo", response_model=list[ExposureAsset])
def get_demo_exposure() -> list[ExposureAsset]:
    """The clearly-labelled demonstration exposure used by the flood MVP."""
    return build_demo_exposure()


@router.get("/vulnerability-functions", response_model=list[VulnerabilityFunction])
def get_vulnerability_functions() -> list[VulnerabilityFunction]:
    return list(VULNERABILITY_FUNCTIONS.values())


@router.get("/models", response_model=list[ModelRegistryEntry])
def get_models() -> list[ModelRegistryEntry]:
    return list_models()


@router.get("/models/{model_id}", response_model=ModelRegistryEntry)
def get_model_card(model_id: str) -> ModelRegistryEntry:
    entry = get_model(model_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Model not found in registry")
    return entry


@router.get("/mitigation-options", response_model=list[MitigationOption])
def get_mitigation_options() -> list[MitigationOption]:
    return list(MITIGATION_OPTIONS.values())


@router.post("/model-runs", response_model=CatModelRunResult)
def create_model_run(
    body: RunRequest,
    repo: MemoryRepository = Depends(repo_dep),
) -> CatModelRunResult:
    """Run the full deterministic flood loss chain on the demo exposure."""
    if body.parent_run_id is not None and repo.get_cat_run(body.parent_run_id) is None:
        raise HTTPException(status_code=404, detail="parent_run_id not found")
    assets, depths = _demo_assets_and_depths()
    terms = FinancialTerms(
        deductible_usd=body.deductible_usd,
        limit_usd=body.limit_usd,
        coinsurance=body.coinsurance,
    )
    result = run_flood_scenario(
        assets, depths, terms,
        scenario_label=body.scenario_label,
        region_label=REGION_LABEL,
        seed=body.seed,
        iterations=body.iterations,
        parent_run_id=body.parent_run_id,
    )
    repo.save_cat_run(result.run_id, result)
    return result


@router.get("/model-runs", response_model=list[RunSummary])
def list_model_runs(repo: MemoryRepository = Depends(repo_dep)) -> list[RunSummary]:
    runs: list[RunSummary] = []
    for run in repo.list_cat_runs():
        assert isinstance(run, CatModelRunResult)
        runs.append(RunSummary(
            run_id=run.run_id,
            scenario_label=run.scenario_label,
            ground_up_p50_usd=run.ground_up_distribution.p50_usd,
            gross_p50_usd=run.gross_distribution.p50_usd,
            confidence=run.confidence.band.value,
        ))
    return runs


def _load_run(repo: MemoryRepository, run_id: str) -> CatModelRunResult:
    run = repo.get_cat_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Model run not found")
    assert isinstance(run, CatModelRunResult)
    return run


@router.get("/model-runs/{run_id}", response_model=CatModelRunResult)
def get_model_run(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> CatModelRunResult:
    return _load_run(repo, run_id)


@router.get("/model-runs/{run_id}/uncertainty")
def get_run_uncertainty(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> dict:
    run = _load_run(repo, run_id)
    return {
        "run_id": run.run_id,
        "ground_up_distribution": run.ground_up_distribution,
        "gross_distribution": run.gross_distribution,
        "net_insured_distribution": run.net_insured_distribution,
        "confidence": run.confidence,
    }


@router.get("/model-runs/{run_id}/probabilistic", response_model=ProbabilisticResult)
def get_run_probabilistic(
    run_id: str,
    years: int = Query(default=5000, ge=1000, le=20000),
    seed: int = 7,
    repo: MemoryRepository = Depends(repo_dep),
) -> ProbabilisticResult:
    """Event-set AAL/OEP/AEP/VaR/TVaR anchored to this run's 100-yr ground-up loss."""
    run = _load_run(repo, run_id)
    events = demo_flood_event_set(run.ground_up_distribution.p50_usd)
    return run_event_set(events, seed=seed, years=years)


@router.post("/model-runs/{run_id}/mitigation", response_model=MitigationResult)
def run_mitigation(
    run_id: str,
    option_id: str = Query(..., min_length=1),
    repo: MemoryRepository = Depends(repo_dep),
) -> MitigationResult:
    _load_run(repo, run_id)  # ensure the run exists
    option = MITIGATION_OPTIONS.get(option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="Mitigation option not found")
    assets, depths = _demo_assets_and_depths()
    return evaluate_mitigation(option, assets, depths)
