# RiskChain — Scientific Model Specification (Flood MVP)

This documents the catastrophe-modelling backend added to the platform. It
implements the transparent calculation chain from the master product prompt for
a single hazard (riverine/flash flood) and a single demonstration region
(Bethlehem / Lehigh Valley, PA). Every number is produced by deterministic,
auditable Python — **no language model calculates any loss** (non-negotiable 4).

## Calculation chain

```
Hazard → Exposure → Vulnerability → Damage → Financial
       → Probabilistic → Uncertainty → Audit → Reporting
```

| Stage | Module | Output |
|-------|--------|--------|
| Hazard | demo depth-at-structure surface (`data/demo/lehigh_valley_exposure.py`) | flood depth (ft) per asset |
| Exposure | `ExposureAsset` (`schemas/catmodel.py`) | assets with per-attribute origin flags |
| Vulnerability | `services/cat/vulnerability.py` | mean damage ratio + damage-state probs |
| Damage | `services/cat/damage.py` | building / contents / BI ground-up loss |
| Financial | `services/cat/financial.py` | ground-up → gross → net insured |
| Uncertainty | `services/cat/uncertainty.py` | Monte Carlo loss distribution (p10/p50/p90) |
| Probabilistic | `services/cat/probabilistic.py` | AAL, OEP, AEP, VaR, TVaR |
| Audit | `services/cat/model_auditor.py` | structured review card |
| Mitigation | `services/cat/mitigation.py` | avoided-loss comparison |
| Registry | `services/cat/model_registry.py` | model cards + approval status |
| Orchestrator | `services/cat/run.py` | immutable `CatModelRunResult` + manifest |

## Hazard inputs

Flood **depth-at-structure** (ft above first-floor grade). The demonstration
surface is a synthetic 100-year event depth per asset. It is explicitly **not** a
FEMA flood-zone designation (non-negotiable 8) and not a survey. Hazard
resolution is recorded as ~10 m and surfaced in the resolution badge.

## Exposure schema

`ExposureAsset` carries occupancy, construction, storeys, year built,
first-floor elevation, floor area, replacement / contents / BI values,
criticality — and an `attribute_origins` map giving each field an
`AttributeOrigin` (`observed`, `user_supplied`, `public_record`, `licensed`,
`model_inferred`, `default_assumption`, `missing`). Inferred/assumed attributes
can never be rendered as observed (non-negotiable 11).

## Vulnerability methodology

Depth-damage curves per occupancy return a **mean damage ratio** by linear
interpolation, plus a coarse damage-state distribution. Curves are
representative demonstration functions marked `approved_for_experimentation`,
never production. Each curve carries a calibration range; depths outside it are
flagged `extrapolated` rather than silently trusted. Contents damage and
downtime use *separate* relationships from structural damage (multipliers
documented as assumptions).

## Damage & financial calculation

```
building_loss  = replacement_value × building_damage_ratio
contents_loss  = contents_value   × contents_damage_ratio
bi_loss        = bi_daily_value   × downtime_days
ground_up      = building_loss + contents_loss + bi_loss

deductible_applied = min(deductible, ground_up)
gross              = clamp(ground_up − deductible_applied, 0, limit)
net_insured        = gross × coinsurance
```

This ordering guarantees the section-27 invariants (higher deductible / lower
limit never increase insured loss), which are unit-tested.

## Probabilistic outputs

An annual event set with occurrence rates λ_e drives:

- **AAL** = Σ λ_e · E[L_e] (computed analytically, cross-checked by simulation)
- **OEP** — distribution of the largest *single* event loss per year
- **AEP** — distribution of *aggregate* loss per year (AEP ≥ OEP at equal RP)
- **VaR / TVaR** — quantile and tail-average of the aggregate annual loss

A **return-period event** (1/λ) and a **return-period loss** (a loss quantile)
are kept distinct and labelled (non-negotiable 9). Loss return periods beyond
the simulation length are not reported.

## Uncertainty

Secondary uncertainty is sampled by drawing each asset's damage ratio from a
Beta distribution (mean = curve value, CoV = curve parameter) and aggregating
per Monte-Carlo iteration. Results are ranges with percentiles — never a single
false-precise figure (principle 2.3). Runs are reproducible from their seed.

## Validation / governance

- **Model registry** records every model with approval status; only
  production/experimental-approved models are runnable. Only deterministic
  policy arithmetic is `approved_for_production`; all hazard/vulnerability
  demonstration models are `approved_for_experimentation`.
- **Model auditor** flags inferred attributes, missing first-floor elevation,
  excluded BI, calibration extrapolation, occupancy/curve mismatch and
  hazard/analysis resolution mismatch.
- **Reproducibility manifest** on every run records code version, model ids,
  seed, parameters and input summary; runs are immutable and never overwritten
  (a re-parameterised run links to its parent).
- **Scientific-behaviour tests** (`tests/test_catmodel.py`) assert monotonic
  damage, zero-exposure/zero-hazard → zero loss, deductible/limit sanity,
  AEP ≥ OEP, and VaR monotonicity.

## What this MVP is NOT

Demonstration curves, synthetic depths and a synthetic event set. Not an
underwriting-grade or regulatory product. The architecture is built so real
FEMA NFHL depths, USACE/Hazus curves, and a calibrated stochastic catalogue can
replace the demonstration components through the model-registry and
formula-review workflow without changing the calculation chain.
