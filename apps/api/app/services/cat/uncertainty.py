"""Uncertainty module (section 10.7).

Secondary uncertainty is represented by sampling each asset's structural damage
ratio from a Beta distribution whose mean is the depth-damage curve value and
whose coefficient of variation comes from the vulnerability function. Losses are
then aggregated across assets per simulation to produce a portfolio loss
distribution - a range with percentiles, never a single false-precise number.

Pure-Python (``random``), deterministic for a given seed, so every run is
reproducible from its manifest (rule 13). No numpy dependency.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean, pstdev

from app.schemas.catmodel import FinancialTerms, LossDistribution
from app.services.cat.damage import contents_damage_ratio, downtime_days
from app.services.cat.financial import apply_terms_amount


@dataclass
class AssetLossSpec:
    asset_id: str
    replacement_value_usd: float
    contents_value_usd: float
    business_interruption_daily_usd: float
    mean_building_ratio: float
    cov: float
    terms: FinancialTerms


def _beta_params(m: float, cov: float) -> tuple[float, float] | None:
    """Beta (alpha, beta) from mean and CoV, or None to use the mean directly."""
    if m <= 0.0 or m >= 1.0 or cov <= 0.0:
        return None
    var = (cov * m) ** 2
    max_var = m * (1.0 - m)
    if var >= max_var:
        var = 0.95 * max_var
    if var <= 0.0:
        return None
    k = (m * (1.0 - m) / var) - 1.0
    alpha = m * k
    beta = (1.0 - m) * k
    if alpha <= 0.0 or beta <= 0.0:
        return None
    return alpha, beta


def _sample_ratio(rng: random.Random, m: float, cov: float) -> float:
    if m <= 0.0:
        return 0.0
    if m >= 1.0:
        return 1.0
    params = _beta_params(m, cov)
    if params is None:
        return m
    return rng.betavariate(*params)


def _percentiles(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list, q in [0,1]."""
    if not sorted_vals:
        return 0.0
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def _distribution(samples: list[float], method: str) -> LossDistribution:
    s = sorted(samples)
    return LossDistribution(
        mean_usd=round(mean(s), 2) if s else 0.0,
        p10_usd=round(_percentiles(s, 0.10), 2),
        p50_usd=round(_percentiles(s, 0.50), 2),
        p90_usd=round(_percentiles(s, 0.90), 2),
        range_low_usd=round(_percentiles(s, 0.10), 2),
        range_high_usd=round(_percentiles(s, 0.90), 2),
        std_usd=round(pstdev(s), 2) if len(s) > 1 else 0.0,
        samples=len(s),
        method=method,
    )


def portfolio_ground_up_samples(
    specs: list[AssetLossSpec],
    seed: int,
    iterations: int = 2000,
) -> list[float]:
    """Raw per-iteration ground-up portfolio losses (for histogram rendering).

    Uses the same sampling scheme and seeding as ``monte_carlo`` so a histogram
    built from these samples is consistent with a run's stored distribution.
    """
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(iterations):
        total = 0.0
        for spec in specs:
            b_ratio = _sample_ratio(rng, spec.mean_building_ratio, spec.cov)
            c_ratio = contents_damage_ratio(b_ratio)
            dt = downtime_days(b_ratio)
            total += (
                spec.replacement_value_usd * b_ratio
                + spec.contents_value_usd * c_ratio
                + spec.business_interruption_daily_usd * dt
            )
        samples.append(total)
    return samples


def monte_carlo(
    specs: list[AssetLossSpec],
    seed: int,
    iterations: int = 2000,
) -> tuple[LossDistribution, LossDistribution, LossDistribution]:
    """Return (ground_up, gross, net) portfolio loss distributions."""
    rng = random.Random(seed)
    gu_samples: list[float] = []
    gross_samples: list[float] = []
    net_samples: list[float] = []

    for _ in range(iterations):
        gu_total = 0.0
        gross_total = 0.0
        net_total = 0.0
        for spec in specs:
            b_ratio = _sample_ratio(rng, spec.mean_building_ratio, spec.cov)
            c_ratio = contents_damage_ratio(b_ratio)
            dt = downtime_days(b_ratio)
            gu = (
                spec.replacement_value_usd * b_ratio
                + spec.contents_value_usd * c_ratio
                + spec.business_interruption_daily_usd * dt
            )
            _, gross, net = apply_terms_amount(gu, spec.terms)
            gu_total += gu
            gross_total += gross
            net_total += net
        gu_samples.append(gu_total)
        gross_samples.append(gross_total)
        net_samples.append(net_total)

    method = f"Monte Carlo, {iterations} iterations, Beta-distributed damage ratios, seed {seed}"
    return (
        _distribution(gu_samples, method),
        _distribution(gross_samples, method),
        _distribution(net_samples, method),
    )
