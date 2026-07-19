"""Scientific-behaviour and API tests for the CAT engine (section 27).

These encode the master prompt's non-negotiable invariants: monotonic damage,
zero exposure -> zero loss, zero hazard -> no hazard loss, deductible/limit
sanity, and OEP <= AEP at equal return period.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data.demo.lehigh_valley_exposure import DEMO_FLOOD_DEPTH_100YR_FT, build_demo_exposure
from app.main import app
from app.schemas.catmodel import FinancialTerms
from app.services.cat.financial import apply_terms_amount
from app.services.cat.probabilistic import analytic_aal, demo_flood_event_set, run_event_set
from app.services.cat.run import run_flood_scenario
from app.services.cat.vulnerability import VULNERABILITY_FUNCTIONS, mean_damage_ratio, select_function


# --- Vulnerability -----------------------------------------------------------

@pytest.mark.parametrize("vf", VULNERABILITY_FUNCTIONS.values(), ids=lambda v: v.function_id)
def test_damage_ratio_is_monotonic_nondecreasing(vf):
    depths = [d / 2 for d in range(-6, 30)]  # -3.0 .. 14.5 ft
    ratios = [mean_damage_ratio(d, vf)[0] for d in depths]
    for earlier, later in zip(ratios, ratios[1:]):
        assert later >= earlier - 1e-9


def test_damage_ratio_flags_extrapolation_outside_calibration():
    vf = select_function("residential")
    _, extrap_low = mean_damage_ratio(vf.calibration_min - 5, vf)
    _, extrap_high = mean_damage_ratio(vf.calibration_max + 5, vf)
    _, in_range = mean_damage_ratio((vf.calibration_min + vf.calibration_max) / 2, vf)
    assert extrap_low and extrap_high and not in_range


# --- Financial invariants ----------------------------------------------------

def test_higher_deductible_never_increases_insured_loss():
    ground_up = 500_000.0
    _, gross_low, _ = apply_terms_amount(ground_up, FinancialTerms(deductible_usd=10_000))
    _, gross_high, _ = apply_terms_amount(ground_up, FinancialTerms(deductible_usd=100_000))
    assert gross_high <= gross_low


def test_lower_limit_never_increases_insured_loss():
    ground_up = 500_000.0
    _, gross_big, _ = apply_terms_amount(ground_up, FinancialTerms(limit_usd=400_000))
    _, gross_small, _ = apply_terms_amount(ground_up, FinancialTerms(limit_usd=100_000))
    assert gross_small <= gross_big


def test_deductible_and_limit_bound_gross_between_zero_and_ground_up():
    for gu in (0.0, 1_000.0, 250_000.0, 9_000_000.0):
        _, gross, net = apply_terms_amount(gu, FinancialTerms(deductible_usd=25_000, limit_usd=1_000_000, coinsurance=0.8))
        assert 0.0 <= gross <= gu
        assert 0.0 <= net <= gross


# --- Zero cases --------------------------------------------------------------

def test_zero_hazard_produces_no_structural_loss():
    assets = build_demo_exposure()
    depths = {a.asset_id: -10.0 for a in assets}  # far below grade -> dry
    result = run_flood_scenario(assets, depths, FinancialTerms(),
                                scenario_label="dry", region_label="demo", iterations=300)
    assert result.ground_up_distribution.p90_usd == 0.0
    assert all(d.building_loss_usd == 0.0 for d in result.asset_damage)


def test_zero_exposure_produces_zero_loss():
    assets = [a.model_copy(update={"replacement_value_usd": 0.0, "contents_value_usd": 0.0,
                                   "business_interruption_daily_usd": 0.0}) for a in build_demo_exposure()]
    result = run_flood_scenario(assets, DEMO_FLOOD_DEPTH_100YR_FT, FinancialTerms(),
                                scenario_label="no value", region_label="demo", iterations=300)
    assert result.ground_up_distribution.range_high_usd == 0.0


# --- Run-level ---------------------------------------------------------------

def test_run_is_reproducible_for_same_seed():
    assets = build_demo_exposure()
    kwargs = dict(scenario_label="s", region_label="demo", seed=999, iterations=500)
    a = run_flood_scenario(assets, DEMO_FLOOD_DEPTH_100YR_FT, FinancialTerms(), **kwargs)
    b = run_flood_scenario(assets, DEMO_FLOOD_DEPTH_100YR_FT, FinancialTerms(), **kwargs)
    assert a.ground_up_distribution.p50_usd == b.ground_up_distribution.p50_usd
    assert a.gross_distribution.mean_usd == b.gross_distribution.mean_usd


def test_run_gross_never_exceeds_ground_up_and_net_never_exceeds_gross():
    assets = build_demo_exposure()
    terms = FinancialTerms(deductible_usd=25_000, limit_usd=3_000_000, coinsurance=0.85)
    result = run_flood_scenario(assets, DEMO_FLOOD_DEPTH_100YR_FT, terms,
                                scenario_label="s", region_label="demo", iterations=500)
    assert result.gross_distribution.mean_usd <= result.ground_up_distribution.mean_usd + 1
    assert result.net_insured_distribution.mean_usd <= result.gross_distribution.mean_usd + 1


def test_exposure_attributes_are_never_all_observed():
    # Guardrail: inferred/assumed attributes must be labelled, not shown as observed.
    for asset in build_demo_exposure():
        assert asset.attribute_origins["construction"].value != "observed"
        assert asset.attribute_origins["replacement_value_usd"].value != "observed"


# --- Probabilistic -----------------------------------------------------------

def test_aal_matches_analytic_sum_of_rate_times_mean():
    events = demo_flood_event_set(10_000_000)
    result = run_event_set(events, seed=1, years=2000)
    assert result.aal_usd == pytest.approx(analytic_aal(events), rel=1e-6)
    assert result.aal_usd > 0


def test_aep_at_least_oep_at_equal_return_period():
    events = demo_flood_event_set(10_000_000)
    result = run_event_set(events, seed=3, years=6000)
    oep = {p.return_period_years: p.loss_usd for p in result.oep_curve}
    for point in result.aep_curve:
        assert point.loss_usd >= oep[point.return_period_years] - 1.0


def test_no_loss_return_period_beyond_simulation_length():
    events = demo_flood_event_set(10_000_000)
    result = run_event_set(events, seed=5, years=100)  # short sim
    assert all(p.return_period_years <= 100 for p in result.oep_curve)
    assert all(p.return_period_years <= 100 for p in result.aep_curve)


def test_var_is_nondecreasing_in_quantile():
    events = demo_flood_event_set(10_000_000)
    result = run_event_set(events, seed=9, years=6000)
    losses = [q.loss_usd for q in sorted(result.var, key=lambda q: q.quantile)]
    for lower, higher in zip(losses, losses[1:]):
        assert higher >= lower


# --- API ---------------------------------------------------------------------

def test_model_run_endpoint_roundtrip():
    client = TestClient(app)
    created = client.post("/api/v1/cat/model-runs", json={"deductible_usd": 25000, "iterations": 400})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    assert client.get(f"/api/v1/cat/model-runs/{run_id}").status_code == 200
    assert client.get(f"/api/v1/cat/model-runs/{run_id}/uncertainty").status_code == 200
    prob = client.get(f"/api/v1/cat/model-runs/{run_id}/probabilistic?years=2000")
    assert prob.status_code == 200 and prob.json()["aal_usd"] > 0
    mit = client.post(f"/api/v1/cat/model-runs/{run_id}/mitigation?option_id=mit-elevate-2ft")
    assert mit.status_code == 200 and mit.json()["avoided_loss_usd"] >= 0
    assert client.get("/api/v1/cat/model-runs/does-not-exist").status_code == 404


def test_registry_lists_only_labelled_models():
    client = TestClient(app)
    models = client.get("/api/v1/cat/models").json()
    assert len(models) >= 4
    # No demonstration model may claim production approval except deterministic arithmetic.
    for model in models:
        if model["approval_status"] == "approved_for_production":
            assert "financial" in model["model_id"] or model["intensity_measure"] == "n/a"
