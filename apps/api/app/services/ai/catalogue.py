"""Approved frontend component catalogue (section 13, deliverable 11).

The copilot may only reference these component types - it cannot emit arbitrary
HTML or JavaScript. Each entry names the component and the data it consumes.
"""

from __future__ import annotations

from app.schemas.copilot import ComponentCatalogueEntry

COMPONENT_CATALOGUE: list[ComponentCatalogueEntry] = [
    ComponentCatalogueEntry(type="loss_range_card", purpose="Modelled loss shown as a range with median and confidence", consumes="CatModelRunResult.ground_up_distribution"),
    ComponentCatalogueEntry(type="uncertainty_card", purpose="Percentiles, Monte Carlo method and confidence drivers", consumes="CatModelRunResult.confidence + distributions"),
    ComponentCatalogueEntry(type="loss_contributors", purpose="Assets ranked by ground-up loss", consumes="CatModelRunResult.asset_damage"),
    ComponentCatalogueEntry(type="ep_curve", purpose="OEP/AEP exceedance-probability curves and AAL", consumes="ProbabilisticResult"),
    ComponentCatalogueEntry(type="mitigation_comparison", purpose="Baseline vs mitigation avoided loss and BCR", consumes="MitigationResult"),
    ComponentCatalogueEntry(type="model_card", purpose="Model registry card with approval status", consumes="ModelRegistryEntry / VulnerabilityFunction"),
    ComponentCatalogueEntry(type="data_quality_card", purpose="Model-auditor findings and limitations", consumes="CatModelRunResult.audit_findings"),
    ComponentCatalogueEntry(type="research_comparison", purpose="List/compare approved methods", consumes="vulnerability functions / registry"),
    ComponentCatalogueEntry(type="source_card", purpose="Provenance for a layer or result", consumes="Provenance"),
    ComponentCatalogueEntry(type="alert_card", purpose="Official alert summary", consumes="Alert"),
]
