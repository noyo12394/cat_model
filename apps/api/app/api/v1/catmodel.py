"""RiskChain catastrophe-model API (sections 22, 24).

Long calculations here are deterministic and fast enough to run inline; each
returns a full, immutable run result with a manifest. A production build would
move these behind the job-queue pattern (return a job id + status), which these
contracts are shaped to allow.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import repo_dep
from app.data.demo.lehigh_valley_exposure import (
    DEMO_FLOOD_DEPTH_100YR_FT,
    build_demo_exposure,
)
from app.db.memory_repository import MemoryRepository
from app.schemas.catmodel import (
    CatModelRunResult,
    CapabilityCoverage,
    DataCoverageItem,
    ExposureAsset,
    FinancialTerms,
    MitigationOption,
    MitigationResult,
    ModelResultLayer,
    ModelRunComparison,
    ModelRunJob,
    ModelRegistryEntry,
    ProbabilisticResult,
    StructuredRunReport,
    VulnerabilityFunction,
)
from app.services.cat.mitigation import MITIGATION_OPTIONS, evaluate_mitigation
from app.services.cat.model_registry import get_model, list_models
from app.services.cat.operational import (
    build_report,
    capability_coverage,
    compare_runs,
    data_coverage,
    result_layer,
)
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


class ProbabilisticPreviewRequest(BaseModel):
    """Stateless event-set preview for serverless deployments.

    The client sends the p50 from the just-returned immutable deterministic
    result.  The approved backend event-set engine, rather than the browser or
    an LLM, then derives the labelled AAL/OEP/AEP output.  This avoids relying
    on in-process run storage between separate serverless invocations.
    """

    median_event_loss_usd: float = Field(gt=0.0)
    years: int = Field(default=5000, ge=1000, le=20000)
    seed: int = 7


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


@router.post("/jobs", response_model=ModelRunJob, status_code=status.HTTP_202_ACCEPTED)
def create_model_run_job(
    body: RunRequest,
    repo: MemoryRepository = Depends(repo_dep),
) -> ModelRunJob:
    """Queue-compatible model-run contract.

    The public Vercel demonstration executes the calculation inline and says so
    explicitly. A production worker can retain this response shape while
    changing ``execution_mode`` and progressing through queued/running states.
    """
    if body.parent_run_id is not None and repo.get_cat_run(body.parent_run_id) is None:
        raise HTTPException(status_code=404, detail="parent_run_id not found")
    submitted = datetime.now(timezone.utc)
    assets, depths = _demo_assets_and_depths()
    result = run_flood_scenario(
        assets,
        depths,
        FinancialTerms(
            deductible_usd=body.deductible_usd,
            limit_usd=body.limit_usd,
            coinsurance=body.coinsurance,
        ),
        scenario_label=body.scenario_label,
        region_label=REGION_LABEL,
        seed=body.seed,
        iterations=body.iterations,
        parent_run_id=body.parent_run_id,
    )
    repo.save_cat_run(result.run_id, result)
    job = ModelRunJob(
        job_id=f"job-{uuid.uuid4().hex[:12]}",
        state="succeeded",
        progress_percent=100,
        submitted_at=submitted,
        completed_at=datetime.now(timezone.utc),
        execution_mode="inline_demo",
        run_id=result.run_id,
        limitations=[
            "This deployment executes the small demonstration run inline; it is not a durable background queue.",
            "Job and run records are in process memory and may not survive a serverless cold start.",
        ],
    )
    repo.save_cat_job(job.job_id, job)
    return job


@router.get("/jobs/{job_id}", response_model=ModelRunJob)
def get_model_run_job(job_id: str, repo: MemoryRepository = Depends(repo_dep)) -> ModelRunJob:
    job = repo.get_cat_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Model job not found")
    assert isinstance(job, ModelRunJob)
    return job


@router.get("/jobs/{job_id}/result", response_model=CatModelRunResult)
def get_model_run_job_result(job_id: str, repo: MemoryRepository = Depends(repo_dep)) -> CatModelRunResult:
    job = get_model_run_job(job_id, repo)
    if job.state != "succeeded" or not job.run_id:
        raise HTTPException(status_code=409, detail="Model job has no completed result")
    return _load_run(repo, job.run_id)


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


@router.get("/model-runs/{run_id}/manifest")
def get_run_manifest(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> dict:
    return _load_run(repo, run_id).manifest.model_dump(mode="json")


@router.get("/model-runs/{run_id}/audit")
def get_run_audit(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> dict:
    run = _load_run(repo, run_id)
    return {
        "run_id": run.run_id,
        "confidence": run.confidence,
        "findings": run.audit_findings,
        "limitations": run.limitations,
    }


@router.get("/model-runs/{run_id}/layers")
def list_run_layers(run_id: str, repo: MemoryRepository = Depends(repo_dep)) -> dict:
    _load_run(repo, run_id)
    return {
        "run_id": run_id,
        "layers": [
            {"layer_id": "flood-depth", "title": "Modelled flood depth at asset", "unit": "ft"},
            {"layer_id": "damage-ratio", "title": "Mean structural damage ratio", "unit": "ratio"},
            {"layer_id": "ground-up-loss", "title": "Ground-up loss by asset", "unit": "USD"},
            {"layer_id": "insured-loss", "title": "Net insured loss by asset", "unit": "USD"},
        ],
    }


@router.get("/model-runs/{run_id}/layers/{layer_id}", response_model=ModelResultLayer)
def get_run_layer(
    run_id: str,
    layer_id: str,
    repo: MemoryRepository = Depends(repo_dep),
) -> ModelResultLayer:
    run = _load_run(repo, run_id)
    try:
        return result_layer(run, layer_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Result layer not found") from exc


@router.post("/model-runs/{run_id}/compare", response_model=ModelRunComparison)
def compare_model_runs(
    run_id: str,
    comparison_run_id: str = Query(..., min_length=1),
    repo: MemoryRepository = Depends(repo_dep),
) -> ModelRunComparison:
    return compare_runs(_load_run(repo, run_id), _load_run(repo, comparison_run_id))


@router.post("/model-runs/{run_id}/reports", response_model=StructuredRunReport)
def create_run_report(
    run_id: str,
    report_type: Literal["executive", "technical", "underwriting", "public"] = "technical",
    repo: MemoryRepository = Depends(repo_dep),
) -> StructuredRunReport:
    return build_report(_load_run(repo, run_id), report_type)


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


@router.post("/probabilistic-preview", response_model=ProbabilisticResult)
def create_probabilistic_preview(body: ProbabilisticPreviewRequest) -> ProbabilisticResult:
    """Derive a demonstrative flood event-set preview without volatile run lookup.

    This is explicitly not a replacement for durable run persistence.  It is a
    safe public-demo transport for the same approved event-set calculation,
    anchored to the returned model-run median supplied by the user interface.
    """
    events = demo_flood_event_set(body.median_event_loss_usd)
    return run_event_set(events, seed=body.seed, years=body.years)


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


@router.get("/data-coverage", response_model=list[DataCoverageItem])
def get_data_coverage() -> list[DataCoverageItem]:
    return data_coverage()


@router.get("/capabilities", response_model=CapabilityCoverage)
def get_capability_coverage() -> CapabilityCoverage:
    return capability_coverage()
