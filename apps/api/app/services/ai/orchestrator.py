"""Copilot orchestrator (section 13).

Flow: interpret intent -> select approved tool(s) -> execute deterministic
backend -> narrate the verified results -> redact any number the narrator was
not handed by a tool. The AI never computes; it routes and explains.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.copilot import (
    Citation,
    CopilotComponent,
    CopilotMode,
    CopilotRequest,
    CopilotResponse,
    MapActionSpec,
    ToolCall,
)
from app.services.ai.guardrails import numbers_source, redact_unsourced_numbers
from app.services.ai.provider import get_provider
from app.services.ai.tools import TOOL_REGISTRY

# Number-free concept definitions for ASK mode (a small Learn-CAT glossary).
GLOSSARY: dict[str, str] = {
    "aal": "Average Annual Loss is the long-term modelled average loss per year; most years are low and a few are extreme, so it is an average, not an expected yearly bill.",
    "oep": "The Occurrence Exceedance Probability curve describes the largest single event loss in a year at a given return period.",
    "aep": "The Aggregate Exceedance Probability curve describes the total loss from all events in a year at a given return period.",
    "var": "Value at Risk is a selected loss quantile - the loss level a chosen probability will not exceed.",
    "tvar": "Tail Value at Risk is the average loss beyond a selected tail threshold, so it captures how bad the worst cases are.",
    "secondary uncertainty": "Secondary uncertainty is the spread of possible damage at a fixed hazard intensity, represented as a distribution rather than a single damage ratio.",
    "fragility": "A fragility curve gives the probability of reaching or exceeding a damage state as hazard intensity increases.",
    "return period": "A return period is the average time between events of a given size; a return-period event is not the same as a return-period loss.",
}


def _infer_mode(message: str, explicit: CopilotMode | None) -> CopilotMode:
    if explicit is not None:
        return explicit
    m = message.lower()
    if any(k in m for k in ("audit", "missing", "double count", "double-count", "calibration", "wrong with")):
        return CopilotMode.AUDIT
    if any(k in m for k in ("mitigat", "elevate", "floodproof", "backup power", "reduce the loss", "reduce loss")):
        return CopilotMode.RUN
    if any(k in m for k in ("aal", "average annual", "oep", "aep", "exceedance", "var", "tvar", "probab")):
        return CopilotMode.ANALYSE
    if any(k in m for k in ("run", "calculate", "loss for", "100-year", "flood loss", "scenario")):
        return CopilotMode.RUN
    if any(k in m for k in ("vulnerability", "depth-damage", "fragility", "which model", "registry", "model card")):
        return CopilotMode.RESEARCH
    if any(k in m for k in ("what is", "explain", "mean", "how do", "define")):
        return CopilotMode.EXPLAIN
    return CopilotMode.ASK


def _select_tools(mode: CopilotMode, message: str) -> list[tuple[str, dict]]:
    m = message.lower()
    if mode == CopilotMode.AUDIT:
        return [("audit_model_run", {})]
    if mode == CopilotMode.RUN and any(k in m for k in ("mitigat", "elevate", "floodproof", "backup", "reduce")):
        option = "mit-elevate-2ft"
        if "floodproof" in m:
            option = "mit-floodproof-3ft"
        elif "backup" in m:
            option = "mit-backup-power"
        return [("run_cat_flood_model", {}), ("test_mitigation", {"option_id": option})]
    if mode == CopilotMode.ANALYSE:
        return [("calculate_aal", {})]
    if mode == CopilotMode.RUN:
        return [("run_cat_flood_model", {})]
    if mode == CopilotMode.RESEARCH:
        if "model card" in m or "registry" in m:
            return [("list_models", {})]
        return [("list_vulnerability_functions", {})]
    return []  # ASK / EXPLAIN conceptual answers use the glossary, no tools


def _glossary_hit(message: str) -> tuple[str, str] | None:
    m = message.lower()
    for term, definition in GLOSSARY.items():
        if term in m:
            return term, definition
    return None


def answer(request: CopilotRequest, repo: MemoryRepository, settings: Settings) -> CopilotResponse:
    mode = _infer_mode(request.message, request.mode)
    selected = _select_tools(mode, request.message)

    tool_trace: list[ToolCall] = []
    components: list[CopilotComponent] = []
    citations: list[Citation] = []
    map_actions: list[MapActionSpec] = []
    tool_summaries: list[str] = []

    for tool_name, args in selected:
        spec = TOOL_REGISTRY.get(tool_name)
        call_id = f"tc-{uuid.uuid4().hex[:8]}"
        if spec is None:
            tool_trace.append(ToolCall(id=call_id, tool=tool_name, arguments=args, status="skipped", summary="Tool not approved."))
            continue
        try:
            result, summary = spec.fn(repo, settings, args)
            tool_trace.append(ToolCall(id=call_id, tool=tool_name, arguments=args, status="ok", summary=summary, result=result))
            tool_summaries.append(summary)
            if spec.descriptor.output_component:
                components.append(CopilotComponent(
                    type=spec.descriptor.output_component,
                    title=spec.descriptor.description,
                    data_reference=call_id,
                ))
            # Highlight the largest-loss assets on the map when a run produced them.
            damage = result.get("asset_damage") if isinstance(result, dict) else None
            if damage:
                top = sorted(damage, key=lambda d: d.get("ground_up_loss_usd", 0), reverse=True)[:3]
                map_actions.append(MapActionSpec(action="highlight_assets", target_ids=[d["asset_id"] for d in top]))
            # Cite the models used.
            for role, model_id in (result.get("manifest", {}).get("model_ids", {}) if isinstance(result, dict) else {}).items():
                citations.append(Citation(source_id=str(model_id), label=f"model:{role}"))
        except Exception as exc:  # keep the copilot resilient
            tool_trace.append(ToolCall(id=call_id, tool=tool_name, arguments=args, status="error", summary=f"Tool failed: {type(exc).__name__}"))

    # Conceptual grounding for ASK/EXPLAIN.
    concept = _glossary_hit(request.message) if mode in (CopilotMode.ASK, CopilotMode.EXPLAIN) else None
    if concept:
        term, definition = concept
        tool_summaries.append(definition)
        citations.append(Citation(source_id=f"glossary:{term}", label="Learn CAT glossary"))

    provider = get_provider(settings)
    raw_message = provider.narrate(mode.value, request.message, tool_summaries)
    message, _ = redact_unsourced_numbers(raw_message, [c.result for c in tool_trace])

    disclaimers = [
        "All figures are demonstration outputs computed by approved deterministic models.",
        "No number in this answer was produced by the language model.",
    ]
    if any(tc.tool in ("run_cat_flood_model", "calculate_aal") for tc in tool_trace):
        disclaimers.append("The scenario uses fixed demonstration exposure and depths; it is not underwriting-grade.")

    return CopilotResponse(
        response_type="scenario_analysis" if components else "explanation",
        mode=mode,
        message=message,
        tool_trace=tool_trace,
        components=components,
        map_actions=map_actions,
        citations=citations,
        disclaimers=disclaimers,
        numbers_source=numbers_source(bool(components)),
        prose_source=provider.name,
        generated_at=datetime.now(timezone.utc),
    )
