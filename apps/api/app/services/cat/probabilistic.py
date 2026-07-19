"""Probabilistic loss module (section 10.5).

Runs an event set with annual occurrence rates to produce AAL, OEP and AEP
curves, VaR and TVaR by simulation. The master prompt's distinctions are kept
explicit:

* A *return-period event* (1/rate) is a property of the hazard event; a
  *return-period loss* is a quantile of the simulated loss distribution. The EP
  curve here is labelled in loss return periods, and the underlying events keep
  their own event return period (rule 9).
* OEP is the distribution of the largest *single* event loss in a year; AEP is
  the distribution of the *aggregate* loss across all events in a year. At the
  same return period AEP >= OEP.

Independence assumption (documented in the result): events occur independently
with Poisson frequency; per-occurrence loss is lognormal with the event's mean
and CoV. This is a demonstration event set, not a calibrated stochastic catalog.
"""

from __future__ import annotations

import math
import random

from app.schemas.catmodel import (
    EPCurvePoint,
    EventDefinition,
    ProbabilisticResult,
    QuantileLoss,
)

DEFAULT_RETURN_PERIODS = [10, 25, 50, 100, 250, 500]
DEFAULT_VAR_QUANTILES = [0.95, 0.99, 0.996]


def demo_flood_event_set(base_100yr_ground_up: float) -> list[EventDefinition]:
    """A small demonstration flood event set anchored to the scenario's 100-yr loss.

    Losses scale with severity; rates are the event annual exceedance rates. The
    100-year event's mean loss is the deterministic scenario ground-up so the two
    views are consistent.
    """
    anchor = max(base_100yr_ground_up, 1.0)
    return [
        EventDefinition(event_id="ev-flood-10yr", name="10-year flood", annual_rate=1 / 10,
                        mean_ground_up_usd=round(anchor * 0.28, 2), loss_cov=0.5, return_period_years=10),
        EventDefinition(event_id="ev-flood-25yr", name="25-year flood", annual_rate=1 / 25,
                        mean_ground_up_usd=round(anchor * 0.50, 2), loss_cov=0.5, return_period_years=25),
        EventDefinition(event_id="ev-flood-50yr", name="50-year flood", annual_rate=1 / 50,
                        mean_ground_up_usd=round(anchor * 0.74, 2), loss_cov=0.5, return_period_years=50),
        EventDefinition(event_id="ev-flood-100yr", name="100-year flood", annual_rate=1 / 100,
                        mean_ground_up_usd=round(anchor, 2), loss_cov=0.55, return_period_years=100),
        EventDefinition(event_id="ev-flood-250yr", name="250-year flood", annual_rate=1 / 250,
                        mean_ground_up_usd=round(anchor * 1.35, 2), loss_cov=0.6, return_period_years=250),
        EventDefinition(event_id="ev-flood-500yr", name="500-year flood", annual_rate=1 / 500,
                        mean_ground_up_usd=round(anchor * 1.7, 2), loss_cov=0.6, return_period_years=500),
    ]


def analytic_aal(events: list[EventDefinition]) -> float:
    """AAL = sum_e lambda_e * E[L_e] (section 10.5)."""
    return sum(e.annual_rate * e.mean_ground_up_usd for e in events)


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's Poisson sampler (fine for the small rates used here)."""
    if lam <= 0:
        return 0
    target = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= target:
            return k
        k += 1


def _lognormal(rng: random.Random, mean_val: float, cov: float) -> float:
    if mean_val <= 0:
        return 0.0
    if cov <= 0:
        return mean_val
    sigma2 = math.log(1 + cov * cov)
    sigma = math.sqrt(sigma2)
    mu = math.log(mean_val) - sigma2 / 2
    return rng.lognormvariate(mu, sigma)


def _ep_points(sorted_desc: list[float], years: int, return_periods: list[int]) -> list[EPCurvePoint]:
    points: list[EPCurvePoint] = []
    n = len(sorted_desc)
    for rp in return_periods:
        if rp > years:
            continue  # do not report a loss return period beyond the simulation length
        ep = 1.0 / rp
        # loss with exceedance probability ep = value at rank ep*n (0-indexed)
        rank = min(n - 1, max(0, int(round(ep * n)) - 1))
        points.append(EPCurvePoint(return_period_years=rp, exceedance_probability=round(ep, 5), loss_usd=round(sorted_desc[rank], 2)))
    return points


def run_event_set(
    events: list[EventDefinition],
    seed: int,
    years: int = 10000,
    return_periods: list[int] | None = None,
    var_quantiles: list[float] | None = None,
    basis: str = "ground_up",
) -> ProbabilisticResult:
    return_periods = return_periods or DEFAULT_RETURN_PERIODS
    var_quantiles = var_quantiles or DEFAULT_VAR_QUANTILES
    rng = random.Random(seed)

    annual_max: list[float] = []  # OEP basis
    annual_agg: list[float] = []  # AEP basis
    for _ in range(years):
        year_losses: list[float] = []
        for ev in events:
            for _ in range(_poisson(rng, ev.annual_rate)):
                year_losses.append(_lognormal(rng, ev.mean_ground_up_usd, ev.loss_cov))
        annual_max.append(max(year_losses) if year_losses else 0.0)
        annual_agg.append(sum(year_losses))

    oep_sorted = sorted(annual_max, reverse=True)
    aep_sorted = sorted(annual_agg, reverse=True)

    # VaR/TVaR on the aggregate annual loss.
    aep_asc = sorted(annual_agg)
    var_points: list[QuantileLoss] = []
    tvar_points: list[QuantileLoss] = []
    for q in var_quantiles:
        idx = min(len(aep_asc) - 1, max(0, int(round(q * len(aep_asc))) - 1))
        var_val = aep_asc[idx]
        tail = aep_asc[idx:]
        tvar_val = sum(tail) / len(tail) if tail else var_val
        var_points.append(QuantileLoss(quantile=q, loss_usd=round(var_val, 2)))
        tvar_points.append(QuantileLoss(quantile=q, loss_usd=round(tvar_val, 2)))

    return ProbabilisticResult(
        basis=basis,
        aal_usd=round(analytic_aal(events), 2),
        event_count=len(events),
        simulation_years=years,
        oep_curve=_ep_points(oep_sorted, years, return_periods),
        aep_curve=_ep_points(aep_sorted, years, return_periods),
        var=var_points,
        tvar=tvar_points,
        method=(
            f"Simulated {years} years; Poisson event frequency, lognormal per-occurrence loss; "
            f"AAL computed analytically as sum of rate x mean loss; seed {seed}."
        ),
        assumptions=[
            "Events occur independently with Poisson annual frequency.",
            "Per-occurrence loss is lognormal with the event's mean and coefficient of variation.",
            "Loss return periods are quantiles of simulated loss - NOT the same as the hazard event return period.",
            "This is a demonstration event set, not a calibrated stochastic catalogue.",
        ],
        limitations=[
            "No spatial correlation, clustering, or seasonality is modelled.",
            "Loss return periods beyond the simulation length are not reported.",
            "AAL and EP curves inherit all limitations of the demonstration vulnerability curves.",
        ],
    )
