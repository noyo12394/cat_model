"""Insurance financial module (section 10.6).

Applies per-location financial terms to a ground-up loss:

    gross  = clamp(ground_up - deductible, 0, limit)
    net    = gross * coinsurance   (insurer's share)

This ordering guarantees the scientific-behaviour invariants (section 27):
raising the deductible never increases the insured loss, and lowering the limit
never increases it either.
"""

from __future__ import annotations

from app.schemas.catmodel import AssetFinancialResult, FinancialTerms


def apply_terms_amount(ground_up: float, terms: FinancialTerms) -> tuple[float, float, float]:
    """Return (deductible_applied, gross, net) for a single ground-up amount."""
    ground_up = max(0.0, ground_up)
    deductible_applied = min(terms.deductible_usd, ground_up)
    after_deductible = ground_up - deductible_applied
    gross = after_deductible if terms.limit_usd is None else min(after_deductible, terms.limit_usd)
    net = gross * terms.coinsurance
    return deductible_applied, gross, net


def apply_terms(asset_id: str, ground_up: float, terms: FinancialTerms) -> AssetFinancialResult:
    deductible_applied, gross, net = apply_terms_amount(ground_up, terms)
    return AssetFinancialResult(
        asset_id=asset_id,
        ground_up_loss_usd=round(ground_up, 2),
        deductible_applied_usd=round(deductible_applied, 2),
        gross_loss_usd=round(gross, 2),
        net_insured_loss_usd=round(net, 2),
        currency=terms.currency,
    )
