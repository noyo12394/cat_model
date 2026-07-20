"""Tests for the chart-data derivations (services/cat/charts.py)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.data.demo.lehigh_valley_exposure import DEMO_FLOOD_DEPTH_100YR_FT, build_demo_exposure
from app.main import app
from app.schemas.catmodel import FinancialTerms
from app.services.cat.charts import (
    fragility_chart,
    fragility_chart_for_asset,
    loss_drivers,
    loss_histogram,
    loss_waterfall,
    water_rise_sweep,
)
from app.services.cat.run import run_flood_scenario


@pytest.fixture(scope="module")
def run():
    return run_flood_scenario(
        build_demo_exposure(), DEMO_FLOOD_DEPTH_100YR_FT,
        FinancialTerms(deductible_usd=25_000, limit_usd=5_000_000, coinsurance=0.9),
        scenario_label="chart test", region_label="demo", seed=4242, iterations=600,
    )


def test_fragility_chart_marks_the_assets_own_point(run):
    dmg = run.asset_damage[0]
    chart = fragility_chart_for_asset(run, dmg.asset_id)
    assert chart is not None
    assert chart.marker is not None
    assert chart.marker.x == dmg.intensity
    assert chart.marker.y == dmg.mean_damage_ratio
    # Curve must be monotone non-decreasing so it draws sensibly.
    ys = [p.y for p in chart.curve]
    assert ys == sorted(ys)


def test_fragility_chart_unknown_function_is_none():
    assert fragility_chart("vf-does-not-exist") is None


def test_histogram_is_consistent_with_run_percentiles(run):
    hist = loss_histogram(run, bins=20)
    assert sum(b.count for b in hist.bins) == hist.samples
    lo = hist.bins[0].lower
    hi = hist.bins[-1].upper
    # The stored run percentiles must fall inside the sampled range.
    assert lo <= hist.p10_usd <= hist.p50_usd <= hist.p90_usd <= hi


def test_waterfall_reconciles_exactly(run):
    wf = loss_waterfall(run)
    ground_up = wf.steps[0].amount_usd
    reductions = sum(-s.amount_usd for s in wf.steps[1:-1])
    net = wf.steps[-1].amount_usd
    assert ground_up - reductions == pytest.approx(net, abs=0.05)
    assert wf.steps[-1].running_total_usd == pytest.approx(net, abs=0.05)
    # No negative running totals.
    assert all(s.running_total_usd >= -0.01 for s in wf.steps)


def test_drivers_shares_sum_and_are_ranked(run):
    drivers = loss_drivers(run, top=5)
    shares = [d.share for d in drivers.drivers]
    assert shares == sorted(shares, reverse=True)
    cumulative = [d.cumulative_share for d in drivers.drivers]
    assert cumulative == sorted(cumulative)
    assert cumulative[-1] <= 1.0 + 1e-9


def test_water_rise_sweep_is_monotone_and_anchored(run):
    sweep = water_rise_sweep(run)
    losses = [p.total_ground_up_usd for p in sweep.points]
    # More water never reduces loss (monotone curves guarantee this).
    for lower, higher in zip(losses, losses[1:]):
        assert higher >= lower - 1e-6
    wet = [p.assets_wet for p in sweep.points]
    for lower, higher in zip(wet, wet[1:]):
        assert higher >= lower
    # The scenario itself sits at offset 0 in the sweep.
    assert any(p.offset_ft == 0.0 for p in sweep.points)


def test_chart_endpoints_roundtrip():
    client = TestClient(app)
    run_id = client.post("/api/v1/cat/model-runs", json={"iterations": 400}).json()["run_id"]
    asset_id = client.get(f"/api/v1/cat/model-runs/{run_id}").json()["asset_damage"][0]["asset_id"]
    for path in (
        f"/api/v1/cat/model-runs/{run_id}/charts/fragility?asset_id={asset_id}",
        f"/api/v1/cat/model-runs/{run_id}/charts/loss-histogram",
        f"/api/v1/cat/model-runs/{run_id}/charts/ep?years=1000",
        f"/api/v1/cat/model-runs/{run_id}/charts/waterfall",
        f"/api/v1/cat/model-runs/{run_id}/charts/drivers",
        f"/api/v1/cat/model-runs/{run_id}/charts/water-rise",
        "/api/v1/cat/charts/fragility/vf-flood-residential-demo",
    ):
        assert client.get(path).status_code == 200, path
    # Serverless-safe: an unknown run id recomputes the deterministic demo run
    # (a cold function instance never saw the original POST) instead of 404-ing
    # and locking the panel.
    recomputed = client.get("/api/v1/cat/model-runs/nope/charts/waterfall?deductible_usd=25000&limit_usd=5000000&coinsurance=0.9")
    assert recomputed.status_code == 200
    assert recomputed.json()["steps"][-1]["amount_usd"] > 0
