"""Historical Analog Finder (section 17 / 31.4).

The similarity score itself is computed with a simple weighted feature-match
function so it is reproducible and explainable; the seeded demo analogs
already carry a score, but this function is what a live implementation would
call once real historical events are ingested (e.g. from OpenFEMA).
"""

from __future__ import annotations

from app.db.memory_repository import MemoryRepository
from app.schemas.inference import HistoricalAnalog

FEATURE_WEIGHTS = {
    "hazard_type": 0.3,
    "watershed": 0.2,
    "season": 0.15,
    "gauge_trajectory": 0.15,
    "warning_progression": 0.1,
    "infrastructure_exposure": 0.1,
}


def score_similarity(shared_features: set[str]) -> float:
    return round(sum(FEATURE_WEIGHTS.get(f, 0.05) for f in shared_features), 2)


def get_analogs_for_incident(repo: MemoryRepository, incident_id: str) -> list[HistoricalAnalog]:
    # In this build all analogs are scoped to the one seeded incident; a
    # multi-incident deployment would filter/rank per-incident here.
    return repo.list_analogs()
