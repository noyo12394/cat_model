from datetime import datetime, timezone

from app.schemas.inference import Scenario
from app.services.scenario_engine import run_scenario


def _scenario(actions: list[str]) -> Scenario:
    return Scenario(
        scenario_id="scn-test",
        name="test",
        created_at=datetime.now(timezone.utc),
        mode="simple",
        location_label="Bethlehem, PA",
        center=(-75.3705, 40.6259),
        hazard_type="flood",
        severity="severe",
        duration_hours=6,
        time_of_day="afternoon",
        actions=actions,
    )


def test_no_action_scenario_has_zero_delta(repo):
    result = run_scenario(repo, _scenario([]))
    assert result.delta["affected_population_change"] == 0
    assert result.delta["travel_time_change_minutes"] == 0.0


def test_closing_road_early_does_not_reduce_population_exposure(repo):
    """Closing a bridge as a precaution doesn't remove the hazard or the
    dependency structure - only the route through it. Population exposure
    must not silently drop to zero as a side effect."""
    result = run_scenario(repo, _scenario(["close_road_early:fac-hill-to-hill-bridge"]))
    assert result.delta["affected_population_change"] == 0
    assert result.with_actions["best_route_label"] != "Via Hill-to-Hill Bridge"


def test_travel_time_never_negative(repo):
    result = run_scenario(repo, _scenario(["reposition_ambulance:fac-bethlehem-fire-1"]))
    assert result.baseline["estimated_emergency_response_minutes"] > 0
    assert result.with_actions["estimated_emergency_response_minutes"] > 0
    assert result.with_actions["best_travel_time_minutes"] >= 0


def test_scenario_result_documents_no_llm_numbers(repo):
    result = run_scenario(repo, _scenario([]))
    assert "language model" in result.method.lower()
