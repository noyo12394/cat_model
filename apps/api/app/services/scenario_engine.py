"""Scenario Lab + Counterfactual Action Lab (sections 25-26).

Per section 26, an LLM is never used to compute a numeric outcome here.
Every number below comes from the same NetworkX cascade engine and routing
approximation used elsewhere in the product, plus an explicit, labeled
assumption table for action costs. An LLM (if configured) may only be asked
to phrase the computed results in prose - see services/assistant.py.

Modeling note: proactively closing a crossing does not remove the physical
hazard or the dependency structure, so it does NOT reduce the cascade's
affected-population estimate (the hospital/fire station/university are still
exposed either way) - it only removes that crossing from the ROUTE options,
which is the honest place for its effect to show up. Repositioning an
ambulance/crew is modeled as a separate emergency-response-time estimate,
never blended into the personal-vehicle route duration.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.memory_repository import MemoryRepository
from app.schemas.inference import Scenario, ScenarioResult
from app.services.cascade import run_cascade
from app.services.route_risk import ROUTE_ID_BY_FACILITY, analyze_route

# Explicit, labeled cost assumptions (order-of-magnitude USD, for demonstration).
ACTION_COST_USD: dict[str, float] = {
    "close_road_early": 0,
    "reposition_ambulance": 800,
    "reposition_crew": 800,
    "add_temporary_pump": 12_000,
    "harden_substation": 250_000,
    "install_backup_power": 45_000,
    "add_secondary_route": 15_000,
    "elevate_structure": 60_000,
    "strengthen_tower": 90_000,
    "issue_warning_earlier": 0,
}

HAZARD_EXPOSED_DEMO_FACILITY = "fac-hill-to-hill-bridge"
BASELINE_EMERGENCY_RESPONSE_MINUTES = 12.0
RESPONSE_TIME_SAVINGS_MINUTES = 8.0
MIN_EMERGENCY_RESPONSE_MINUTES = 3.0


def _parse_actions(actions: list[str]) -> dict:
    closed_route_facilities: list[str] = []
    redundancy: list[tuple[str, str]] = []
    response_adjustment = 0.0
    cost = 0.0
    parsed_labels: list[str] = []

    for action in actions:
        parts = action.split(":")
        kind = parts[0]
        cost += ACTION_COST_USD.get(kind, 0)
        if kind == "close_road_early" and len(parts) > 1:
            closed_route_facilities.append(parts[1])
            parsed_labels.append(f"Close {parts[1]} earlier than an official closure would occur")
        elif kind == "add_secondary_route" and len(parts) > 2:
            redundancy.append((parts[1], parts[2]))
            parsed_labels.append(f"Add a secondary route between {parts[1]} and {parts[2]}")
        elif kind in ("reposition_ambulance", "reposition_crew"):
            response_adjustment -= RESPONSE_TIME_SAVINGS_MINUTES
            parsed_labels.append(
                f"Reposition {'an ambulance' if kind == 'reposition_ambulance' else 'a crew'} ahead of impact"
            )
        else:
            parsed_labels.append(kind.replace("_", " "))

    return {
        "closed_route_facilities": closed_route_facilities,
        "redundancy": redundancy,
        "response_adjustment": response_adjustment,
        "cost": cost,
        "labels": parsed_labels,
    }


def _summarize(
    repo: MemoryRepository,
    closed_route_facilities: list[str],
    redundancy: list[tuple[str, str]],
    response_adjustment: float,
) -> dict:
    # The hazard and dependency structure are unaffected by route-only
    # actions (e.g. closing a bridge), so the cascade is always run without
    # facility removal here; "added_redundancy_edges" is the one lever that
    # genuinely changes connectivity.
    cascade = run_cascade(
        repo,
        hazard_facility_ids=[HAZARD_EXPOSED_DEMO_FACILITY],
        added_redundancy_edges=redundancy,
    )
    affected_population = sum(
        n.served_population for n in cascade.nodes if n.hops_from_hazard is not None
    )

    routes = analyze_route(repo, "lehigh-university", "fac-stlukes-bethlehem")
    closed_route_ids = {ROUTE_ID_BY_FACILITY[f] for f in closed_route_facilities if f in ROUTE_ID_BY_FACILITY}
    usable = [
        r
        for r in routes
        if r.exposure_level != "unavailable" and r.duration_minutes and r.route_id not in closed_route_ids
    ]
    best_route = min(usable, key=lambda r: r.duration_minutes) if usable else None

    response_minutes = max(
        MIN_EMERGENCY_RESPONSE_MINUTES, BASELINE_EMERGENCY_RESPONSE_MINUTES + response_adjustment
    )

    return {
        "affected_population_estimate": affected_population,
        "best_travel_time_minutes": best_route.duration_minutes if best_route else None,
        "best_route_label": best_route.label if best_route else "No usable route found",
        "estimated_emergency_response_minutes": round(response_minutes, 1),
        "cascade_narrative": cascade.narrative,
    }


def run_scenario(repo: MemoryRepository, scenario: Scenario) -> ScenarioResult:
    baseline = _summarize(repo, closed_route_facilities=[], redundancy=[], response_adjustment=0.0)

    parsed = _parse_actions(scenario.actions)
    with_actions = _summarize(
        repo,
        closed_route_facilities=parsed["closed_route_facilities"],
        redundancy=parsed["redundancy"],
        response_adjustment=parsed["response_adjustment"],
    )

    travel_time_change = (
        round(with_actions["best_travel_time_minutes"] - baseline["best_travel_time_minutes"], 1)
        if with_actions["best_travel_time_minutes"] is not None
        and baseline["best_travel_time_minutes"] is not None
        else None
    )

    delta = {
        "affected_population_change": with_actions["affected_population_estimate"]
        - baseline["affected_population_estimate"],
        "travel_time_change_minutes": travel_time_change,
        "emergency_response_change_minutes": round(
            with_actions["estimated_emergency_response_minutes"]
            - baseline["estimated_emergency_response_minutes"],
            1,
        ),
        "actions_tested": parsed["labels"],
        "estimated_cost_usd": parsed["cost"],
    }

    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        computed_at=datetime.now(timezone.utc),
        baseline=baseline,
        with_actions=with_actions,
        delta=delta,
        assumptions=[
            f"Hazard exposure is anchored on {HAZARD_EXPOSED_DEMO_FACILITY} (seeded Bethlehem scenario).",
            "Action costs are order-of-magnitude planning assumptions, not appraisals.",
            f"Baseline emergency response time is assumed at {BASELINE_EMERGENCY_RESPONSE_MINUTES:.0f} minutes; "
            f"repositioning an ambulance/crew is assumed to save {RESPONSE_TIME_SAVINGS_MINUTES:.0f} minutes, "
            f"floored at {MIN_EMERGENCY_RESPONSE_MINUTES:.0f} minutes.",
            "Closing a crossing early removes it from route options but does not change the underlying hazard "
            "or dependency exposure - the population/infrastructure exposure numbers reflect that.",
            "Affected-population figures come from facility 'served_population' fields, which are approximate.",
        ],
        uncertainty_notes=[
            "This scenario reuses the seeded demo infrastructure graph; it is not a calibrated hydraulic or traffic model.",
            "Remaining uncertainty is not reduced to zero by any tested action - treat deltas as directional, not exact.",
        ],
    )
