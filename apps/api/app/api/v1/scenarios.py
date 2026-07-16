from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import repo_dep
from app.data.demo.lehigh_valley_flood import BETHLEHEM_CENTER
from app.db.memory_repository import MemoryRepository
from app.schemas.inference import Scenario, ScenarioResult
from app.services.scenario_engine import run_scenario

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class ScenarioCreateRequest(BaseModel):
    name: str = "Untitled scenario"
    mode: str = Field(default="simple", pattern="^(simple|advanced)$")
    location_label: str = "Bethlehem, PA"
    center: tuple[float, float] = BETHLEHEM_CENTER
    hazard_type: str = "flood"
    severity: str = "severe"
    duration_hours: float = 6.0
    time_of_day: str = "weekday_afternoon"
    river_condition: str | None = "already_elevated"
    advanced_params: dict[str, float | str] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)


@router.post("", response_model=Scenario)
def create_scenario(
    body: ScenarioCreateRequest, repo: MemoryRepository = Depends(repo_dep)
) -> Scenario:
    scenario = Scenario(
        scenario_id=f"scn-{uuid.uuid4().hex[:10]}",
        name=body.name,
        created_at=datetime.now(timezone.utc),
        mode=body.mode,
        location_label=body.location_label,
        center=body.center,
        hazard_type=body.hazard_type,
        severity=body.severity,
        duration_hours=body.duration_hours,
        time_of_day=body.time_of_day,
        river_condition=body.river_condition,
        advanced_params=body.advanced_params,
        actions=body.actions,
    )
    repo.save_scenario(scenario)
    return scenario


@router.post("/{scenario_id}/run", response_model=ScenarioResult)
def run(scenario_id: str, repo: MemoryRepository = Depends(repo_dep)) -> ScenarioResult:
    scenario = repo.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found. Create it first with POST /scenarios.")
    result = run_scenario(repo, scenario)
    repo.save_scenario_result(result)
    return result


@router.get("/{scenario_id}/results", response_model=ScenarioResult)
def get_results(scenario_id: str, repo: MemoryRepository = Depends(repo_dep)) -> ScenarioResult:
    result = repo.get_scenario_result(scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail="No results yet. Run the scenario first with POST /scenarios/{id}/run.")
    return result
