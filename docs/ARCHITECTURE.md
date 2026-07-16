# Architecture

## Data flow (implemented)

```text
Official feeds and APIs (NWS, USGS, FIRMS, AirNow, OpenFEMA, Google Maps Platform)
        v
Typed adapters (apps/api/app/adapters/*) - real HTTP call if configured, else demo fallback
        v
Common data model (apps/api/app/schemas/*) - every record carries certainty_class + provenance
        v
In-memory repository (apps/api/app/db/memory_repository.py) - seeded from
apps/api/app/data/demo/lehigh_valley_flood.py
        v
Services (apps/api/app/services/*) - fusion, nowcasting, cascade, route risk,
scenario engine, sensor health, evidence, source health, assistant
        v
FastAPI routers (apps/api/app/api/v1/*)
        v
Next.js frontend (apps/web/src) - map, shell, signature-feature components
```

The frontend never calls NWS/USGS/FIRMS/AirNow/Google directly - it only ever talks to
the backend, which is what protects credentials, normalizes data, and lets every
response carry a consistent freshness/confidence signal (section 35 of the master prompt).

## Why an in-memory repository instead of Postgres/PostGIS today

`infra/migrations/0001_init.sql` defines the intended production schema in full -
hazard events, alerts, forecasts, sensor observations, facilities, dependencies,
incidents, timelines, historical analogs, scenarios, scenario results, annotations, and
tenant-isolated portfolios. `docker-compose.yml` runs a real PostGIS + Redis stack.

The API's business logic, however, is written against a small repository interface
(`MemoryRepository`) rather than direct SQL, and that repository currently keeps state
in-process. This was a deliberate scoping decision for this build: it keeps the API
runnable with zero external dependencies (`uvicorn app.main:app` and nothing else),
which matters for a demo-first product per section 46 of the master prompt. Swapping in
a real Postgres-backed repository means implementing the same interface
(`list_facilities`, `get_incident`, `save_scenario`, etc.) against SQL queries - the
services and API routers do not need to change.

## Map engine selection

`apps/web/src/components/map/MapView.tsx` picks between two implementations at
runtime based on whether `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is set:

- **MapLibreView** (default): MapLibre GL JS against OpenStreetMap raster tiles. No key
  required. This is what makes the product usable out of the box (section 46). Note:
  `tile.openstreetmap.org` is used here for convenience; a production deployment should
  use a properly licensed tile provider (Google Maps Platform, MapTiler, Stadia, etc.)
  per OSM's tile usage policy.
- **GoogleMapView**: loads the Google Maps JavaScript API dynamically and renders the
  same facility markers / incident geometry / route polylines through the native
  `google.maps.*` API, including Street View support. Requires a **browser-restricted**
  key (see `SECURITY.md` / `COST_PLAN.md`).

Both implementations read from the same `useMapData` hook and the same Zustand store
(`flyToTarget`, `layers`), so switching engines does not change any other component.

## State management

`apps/web/src/lib/store.ts` is a single Zustand store holding: the active mode (Live /
Forecast / Replay / Scenario Lab / Portfolio), the right panel's content descriptor,
time-bar offset/playback state, layer visibility, the uncertainty lens toggle, saved
places, and the map's fly-to target. Server data (incidents, capsules, routes,
scenarios, assistant answers) is fetched with React Query and is never duplicated into
the Zustand store.

### Why the map persists across "pages"

The map, search bar, nav rail, right-panel host, and time bar are rendered once, in the
root layout (`apps/web/src/app/layout.tsx` -> `AppShell`). Individual routes
(`/forecast`, `/replay`, `/scenario-lab`, `/incidents/[slug]`, ...) render a tiny
`ModeSetter` client component that only pushes the intended mode/panel into the shared
store on mount. This gives Incident Rooms a real, shareable URL (section 9's
requirement) without remounting the map on every navigation.

## AI services and the "no LLM for numbers" rule

Every AI-labeled feature in this build (Event Fusion, Impact Nowcasting, Living
Cascade, Route Risk, the Scenario/Counterfactual engine, Sensor Health, Historical
Analog) is implemented as deterministic, inspectable Python: rule chains, graph
algorithms (NetworkX breadth-first propagation), and geometric overlap checks - never
a language model. This matches section 26 and 31.2 of the master prompt directly. See
`docs/AI_SERVICES.md` for the mapping from each spec'd AI system to its implementation,
and `docs/MODEL_CARDS.md` for per-model cards.

The Grounded AI Assistant (`apps/api/app/services/assistant.py`) is retrieval +
template based by default (works fully offline) with a documented, currently-inert
extension point for an LLM to polish prose - never to invent facts, numbers, or
probabilities.
