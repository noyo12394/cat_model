"""In-memory repository implementing the common data model.

This is the storage backend the MVP actually runs against. It intentionally
implements the same shape the PostGIS schema in ``infra/migrations`` defines
(see docs/ARCHITECTURE.md) so that swapping in a real Postgres/PostGIS-backed
repository later is a matter of implementing this same interface against SQL
queries, not rewriting the services or API layer that consume it.

Section 50 forbids "fake production integrations" - this repository is not
pretending to be Postgres. It is a genuine, working repository; it just
keeps state in-process, seeded from the demo dataset and any adapters that
successfully reach a live source.
"""

from __future__ import annotations

from functools import lru_cache

from app.data.demo.lehigh_valley_flood import PLACE_DIRECTORY, build_flood_scenario
from app.schemas.event import Alert, Forecast, HazardEvent, SensorObservation
from app.schemas.facility import Facility, InfrastructureDependency
from app.schemas.incident import IncidentDetail
from app.schemas.inference import HistoricalAnalog, Scenario, ScenarioResult


class MemoryRepository:
    def __init__(self) -> None:
        self._live = build_flood_scenario(mode="live_demo")
        self._replay = build_flood_scenario(mode="replay")
        self._scenarios: dict[str, Scenario] = {}
        self._scenario_results: dict[str, ScenarioResult] = {}
        self._portfolios: dict[str, dict] = {}
        # Immutable CAT model runs, keyed by run_id (rule 13: never overwrite).
        self._cat_runs: dict[str, object] = {}
        self._cat_jobs: dict[str, object] = {}

    # -- scenarios --------------------------------------------------------
    def save_scenario(self, scenario: Scenario) -> None:
        self._scenarios[scenario.scenario_id] = scenario

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return self._scenarios.get(scenario_id)

    def save_scenario_result(self, result: ScenarioResult) -> None:
        self._scenario_results[result.scenario_id] = result

    def get_scenario_result(self, scenario_id: str) -> ScenarioResult | None:
        return self._scenario_results.get(scenario_id)

    # -- CAT model runs (immutable) ---------------------------------------
    def save_cat_run(self, run_id: str, result: object) -> None:
        if run_id in self._cat_runs:
            raise ValueError(f"CAT run {run_id} is immutable and already exists")
        self._cat_runs[run_id] = result

    def get_cat_run(self, run_id: str) -> object | None:
        return self._cat_runs.get(run_id)

    def list_cat_runs(self) -> list[object]:
        return list(self._cat_runs.values())

    # -- CAT jobs (queue-compatible contract; inline in demo runtime) -----
    def save_cat_job(self, job_id: str, job: object) -> None:
        if job_id in self._cat_jobs:
            raise ValueError(f"CAT job {job_id} is immutable and already exists")
        self._cat_jobs[job_id] = job

    def get_cat_job(self, job_id: str) -> object | None:
        return self._cat_jobs.get(job_id)

    # -- portfolio (tenant-isolated by portfolio_id token) -----------------
    def save_portfolio(self, portfolio_id: str, data: dict) -> None:
        self._portfolios[portfolio_id] = data

    def get_portfolio(self, portfolio_id: str) -> dict | None:
        return self._portfolios.get(portfolio_id)

    # -- facilities ---------------------------------------------------
    def list_facilities(self) -> list[Facility]:
        return list(self._live.facilities)

    def get_facility(self, facility_id: str) -> Facility | None:
        for f in self._live.facilities:
            if f.facility_id == facility_id:
                return f
        return None

    # -- alerts / forecasts / events / sensors -------------------------
    def list_alerts(self, mode: str = "live") -> list[Alert]:
        return list(self._replay.alerts if mode == "replay" else self._live.alerts)

    def list_forecasts(self, mode: str = "live") -> list[Forecast]:
        return list(self._replay.forecasts if mode == "replay" else self._live.forecasts)

    def list_events(self, mode: str = "live") -> list[HazardEvent]:
        return list(self._replay.events if mode == "replay" else self._live.events)

    def list_sensors(self, mode: str = "live") -> list[SensorObservation]:
        return list(self._replay.sensors if mode == "replay" else self._live.sensors)

    def sensor_series(self, sensor_id: str, mode: str = "live") -> list[SensorObservation]:
        obs = self.list_sensors(mode=mode)
        series = [o for o in obs if o.sensor_id == sensor_id]
        return sorted(series, key=lambda o: o.observed_at)

    # -- incidents ------------------------------------------------------
    def list_incidents(self, mode: str = "live") -> list[IncidentDetail]:
        scenario = self._replay if mode == "replay" else self._live
        return [scenario.incident] if scenario.incident else []

    def get_incident(self, incident_id: str, mode: str = "live") -> IncidentDetail | None:
        for inc in self.list_incidents(mode=mode):
            if inc.incident_id == incident_id or inc.slug == incident_id:
                return inc
        return None

    # -- dependencies / analogs ------------------------------------------
    def list_dependencies(self) -> list[InfrastructureDependency]:
        return list(self._live.dependencies)

    def list_analogs(self) -> list[HistoricalAnalog]:
        return list(self._live.analogs)

    # -- places -----------------------------------------------------------
    def search_places(self, query: str, limit: int = 8) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return []
        scored: list[tuple[float, dict]] = []
        for place in PLACE_DIRECTORY.values():
            names = [place["name"].lower(), *place.get("aliases", [])]
            score = 0.0
            for name in names:
                if q == name:
                    score = max(score, 1.0)
                elif name.startswith(q):
                    score = max(score, 0.85)
                elif q in name:
                    score = max(score, 0.6)
            if score > 0:
                scored.append((score, place))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_place(self, place_id: str) -> dict | None:
        return PLACE_DIRECTORY.get(place_id)

    def nearest_facilities(
        self, center: tuple[float, float], limit: int = 5
    ) -> list[tuple[Facility, float]]:
        from app.services.geo import haversine_km

        ranked = [
            (f, haversine_km(center, (f.geometry.coordinates[0], f.geometry.coordinates[1])))
            for f in self.list_facilities()
            if f.geometry.type == "Point"
        ]
        ranked.sort(key=lambda pair: pair[1])
        return ranked[:limit]


@lru_cache
def get_repository() -> MemoryRepository:
    return MemoryRepository()
