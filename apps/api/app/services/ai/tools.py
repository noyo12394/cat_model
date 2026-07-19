"""Approved tool registry for the copilot (section 13).

Each tool wraps an *approved deterministic backend function*. The AI may request
a tool; the application executes it and returns a structured result. Every
number the copilot ever shows originates in one of these results - the language
model only narrates. Tool ``summary`` strings are deliberately number-free so
the narrator cannot echo a figure into prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.config import Settings
from app.data.demo.lehigh_valley_exposure import (
    DEMO_FLOOD_DEPTH_100YR_FT,
    build_demo_exposure,
)
from app.db.memory_repository import MemoryRepository
from app.schemas.catmodel import CatModelRunResult, FinancialTerms
from app.schemas.copilot import ToolDescriptor
from app.services.cat.mitigation import MITIGATION_OPTIONS, evaluate_mitigation
from app.services.cat.model_registry import get_model, list_models
from app.services.cat.probabilistic import demo_flood_event_set, run_event_set
from app.services.cat.run import run_flood_scenario
from app.services.cat.vulnerability import VULNERABILITY_FUNCTIONS, select_function

REGION_LABEL = "Bethlehem / Lehigh Valley, PA (demonstration)"

ToolResult = tuple[dict[str, Any], str]  # (structured result, number-free summary)
ToolFn = Callable[[MemoryRepository, Settings, dict[str, Any]], ToolResult]


@dataclass(frozen=True)
class ToolSpec:
    fn: ToolFn
    descriptor: ToolDescriptor


def _f(args: dict, key: str, default: float) -> float:
    try:
        return float(args.get(key, default))
    except (TypeError, ValueError):
        return default


def _fresh_run(repo: MemoryRepository, args: dict) -> CatModelRunResult:
    terms = FinancialTerms(
        deductible_usd=max(0.0, _f(args, "deductible_usd", 25_000)),
        limit_usd=(None if args.get("limit_usd") in (None, "", 0) else max(0.0, _f(args, "limit_usd", 5_000_000))),
        coinsurance=min(1.0, max(0.0, _f(args, "coinsurance", 1.0))),
    )
    iterations = int(min(5000, max(200, _f(args, "iterations", 2000))))
    result = run_flood_scenario(
        build_demo_exposure(), DEMO_FLOOD_DEPTH_100YR_FT, terms,
        scenario_label=str(args.get("scenario_label", "100-year flood (demonstration)")),
        region_label=REGION_LABEL, seed=int(_f(args, "seed", 12345)), iterations=iterations,
    )
    repo.save_cat_run(result.run_id, result)
    return result


def _load_or_run(repo: MemoryRepository, args: dict) -> CatModelRunResult:
    run_id = args.get("run_id")
    if run_id:
        existing = repo.get_cat_run(str(run_id))
        if isinstance(existing, CatModelRunResult):
            return existing
    return _fresh_run(repo, args)


# -- tool implementations -----------------------------------------------------

def tool_run_flood_model(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    run = _fresh_run(repo, args)
    return run.model_dump(mode="json"), (
        "I ran the approved flood loss chain on the demonstration exposure; "
        "the loss range, uncertainty and assumptions are in the cards below."
    )


def tool_calculate_aal(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    run = _load_or_run(repo, args)
    prob = run_event_set(demo_flood_event_set(run.ground_up_distribution.p50_usd), seed=7, years=5000)
    result = prob.model_dump(mode="json")
    result["run_id"] = run.run_id
    return result, (
        "I computed the average annual loss and the exceedance-probability curves "
        "from the demonstration event set; a return-period loss is not the same as a return-period event."
    )


def tool_test_mitigation(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    option_id = str(args.get("option_id", "mit-elevate-2ft"))
    option = MITIGATION_OPTIONS.get(option_id)
    if option is None:
        return {"error": "unknown_option", "available": list(MITIGATION_OPTIONS)}, (
            "That mitigation option is not in the approved list; I showed the available options instead."
        )
    result = evaluate_mitigation(option, build_demo_exposure(), DEMO_FLOOD_DEPTH_100YR_FT)
    return result.model_dump(mode="json"), (
        "I compared the scenario with and without the selected mitigation; the avoided loss is a "
        "single-scenario figure, not an avoided average annual loss."
    )


def tool_get_model_card(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    entry = get_model(str(args.get("model_id", "")))
    if entry is None:
        return {"error": "not_found"}, "I could not find that model in the registry."
    return entry.model_dump(mode="json"), "I retrieved the model card and its approval status."


def tool_recommend_model(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    occupancy = str(args.get("occupancy", "residential"))
    vf = select_function(occupancy)
    return vf.model_dump(mode="json"), (
        "I recommended an approved vulnerability function for that occupancy; it is experimental, "
        "so treat its output as demonstration only."
    )


def tool_list_vulnerability_functions(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    fns = [
        {"function_id": vf.function_id, "name": vf.name, "asset_class": vf.asset_class,
         "approval_status": vf.approval_status.value}
        for vf in VULNERABILITY_FUNCTIONS.values()
    ]
    return {"functions": fns}, "I listed the approved vulnerability functions and their approval status."


def tool_audit_run(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    run = _load_or_run(repo, args)
    return {
        "run_id": run.run_id,
        "audit_findings": [f.model_dump(mode="json") for f in run.audit_findings],
        "confidence": run.confidence.model_dump(mode="json"),
        "limitations": run.limitations,
    }, "I reviewed the model run for data-quality, calibration and resolution issues."


def tool_list_models(repo: MemoryRepository, settings: Settings, args: dict) -> ToolResult:
    return {"models": [m.model_dump(mode="json") for m in list_models()]}, (
        "I listed the models in the registry with their approval status."
    )


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "run_cat_flood_model": ToolSpec(tool_run_flood_model, ToolDescriptor(
        name="run_cat_flood_model", description="Run the deterministic flood loss chain on demo exposure.",
        approved=True, computes_numbers=True, output_component="loss_range_card")),
    "calculate_aal": ToolSpec(tool_calculate_aal, ToolDescriptor(
        name="calculate_aal", description="Compute AAL and OEP/AEP/VaR/TVaR from the event set.",
        approved=True, computes_numbers=True, output_component="ep_curve")),
    "test_mitigation": ToolSpec(tool_test_mitigation, ToolDescriptor(
        name="test_mitigation", description="Compare baseline vs a mitigation option.",
        approved=True, computes_numbers=True, output_component="mitigation_comparison")),
    "get_model_card": ToolSpec(tool_get_model_card, ToolDescriptor(
        name="get_model_card", description="Retrieve a model registry card.",
        approved=True, computes_numbers=False, output_component="model_card")),
    "recommend_model": ToolSpec(tool_recommend_model, ToolDescriptor(
        name="recommend_model", description="Recommend an approved vulnerability function.",
        approved=True, computes_numbers=False, output_component="model_card")),
    "list_vulnerability_functions": ToolSpec(tool_list_vulnerability_functions, ToolDescriptor(
        name="list_vulnerability_functions", description="List approved vulnerability functions.",
        approved=True, computes_numbers=False, output_component="research_comparison")),
    "list_models": ToolSpec(tool_list_models, ToolDescriptor(
        name="list_models", description="List the model registry.",
        approved=True, computes_numbers=False, output_component="research_comparison")),
    "audit_model_run": ToolSpec(tool_audit_run, ToolDescriptor(
        name="audit_model_run", description="Run the model auditor over a run.",
        approved=True, computes_numbers=False, output_component="data_quality_card")),
}


def list_tool_descriptors() -> list[ToolDescriptor]:
    return [spec.descriptor for spec in TOOL_REGISTRY.values()]
