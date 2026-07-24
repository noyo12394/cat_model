# EarthPulse

A global and local intelligence platform for hazards, infrastructure and community impacts. Map-first
situational awareness that connects a developing hazard to real places, routes, and
infrastructure dependencies - while keeping every AI conclusion traceable to evidence.

This repository is the first functioning build: a working FastAPI backend and Next.js
frontend, connected to the live GDACS global event feed and seeded with one polished demonstration scenario (a developing flood near
Bethlehem, PA / Lehigh Valley), following the phased scope in `docs/PRD.md`.

**Start here:**

- [`docs/PRD.md`](docs/PRD.md) - product requirements and what "done" means for this build
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - system design and key decisions
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) - what is real vs. scoped out, and why
- [`docs/PARTNER_READINESS.md`](docs/PARTNER_READINESS.md) - industry-partner walkthrough, evidence posture and operational delivery gates
- [`docs/CATASTROPHE_GENOME.md`](docs/CATASTROPHE_GENOME.md) - 3D live-event atlas and source-linked historical metadata laboratory, including its strict non-modelling limits

## Quickstart (no API keys required)

### Option A: Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### Option B: run each app locally

Backend:

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional - every value is optional
uvicorn app.main:app --reload --port 8000
```

Frontend (in a second terminal):

```bash
cd apps/web
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```

Then open http://localhost:3000. Search **"Lehigh University"** to walk through the
signature flow described in `docs/PRD.md` section 1: Location Capsule -> developing
incident -> What may happen next -> Route Risk -> Scenario Lab.

No API keys are required for any of this - see [Demo mode vs. live mode](#demo-mode-vs-live-mode)
below.

## Traceable CAT Model workflow

The Model page separates Live Event, Historical Event, Hypothetical /
Return-Period, and Sample Demonstration workflows. The source-backed path
integrates Photon/OpenStreetMap and Nominatim geocoding, U.S. Census containing
geographies, NHC active storms, USGS FDSN earthquakes and ShakeMap contours,
NWS active flood-alert polygons, FEMA effective NFHL flood zones, and USACE
NSI 2026 Base exposure.

FEMA zone membership does not provide building-level flood depth. Those runs
therefore report exposure only and never calculate dollar damage. The bundled
Bethlehem loss model is available only through **Use sample demonstration**,
is permanently labelled Demo, and is never mixed with live source data.

New routes are `GET /api/v1/places/resolve`, `GET
/api/v1/cat/hazard-events`, `GET
/api/v1/cat/hazard-events/{hazard_type}/{event_id}`, and `POST
/api/v1/cat/analyses`. Each run embeds a reproducibility manifest containing
resolved geography, provider event/advisory IDs, source retrieval records,
missing and excluded inputs, seed/count, code version, assumptions, and the
calculation summary.

No key is required for NHC, USGS, FEMA NFHL, USACE NSI, Census Geocoder,
Nominatim, or Photon. Keep `NASA_FIRMS_MAP_KEY`, `CENSUS_API_KEY`, map-provider
keys, and database credentials server-side unless a variable is explicitly a
browser-restricted `NEXT_PUBLIC_*` map key.

Known coverage gaps are stated in the UI: historical NHC best-track search,
historical flood/fire footprint adapters, live flood inundation (NWS alert
areas are not inundation), ACS profiles, ShakeMap tract aggregation, durable
cross-instance run storage, and production vulnerability/loss functions remain
unavailable.

## Catastrophe Genome Lab

The **Genome Lab** is an optional visual-navigation layer in the web workspace.
Its 3D atlas uses the live GDACS event centres already retrieved by the app and
a separate, source-linked catalogue of 30 historical event metadata records.
The accompanying 30-trait helix and nearest-neighbour comparison are
deterministic catalogue navigation only—not a loss model, analogue engine,
fragility curve, forecast, event footprint, or severity score. See
[`docs/CATASTROPHE_GENOME.md`](docs/CATASTROPHE_GENOME.md) for the full
provenance and method.

## Repository layout

```text
apps/
  api/     FastAPI backend - schemas, adapters, services, API routes, tests
  web/     Next.js frontend - map, shell, signature-feature components
infra/
  migrations/   PostGIS schema (source of truth for the intended production schema)
docs/          Product, architecture, security, cost, test, and model documentation
docker-compose.yml
```

## Demo mode vs. live mode

Every external data source (GDACS, NWS, USGS Water, USGS Earthquakes, NASA FIRMS, AirNow,
OpenFEMA, Google Maps Platform) has a typed adapter in `apps/api/app/adapters/`. Each
adapter tries the real public API first when credentials/config are present, and falls
back to a clearly-labeled demo provider on any failure (missing key, timeout, non-2xx).
Nothing is silently faked as live - see the `data_status` field (`live` / `stale` /
`unavailable` / `demo`) on every response, and `GET /api/v1/sources/status` for a live
readout of which feeds are actually reachable right now.

See `apps/api/.env.example` and `apps/web/.env.example` for exactly which environment
variables unlock which real integrations.

## Running tests

```bash
cd apps/api && source .venv/bin/activate && python -m pytest
cd apps/web && npm run lint && npm run build
```

## Trust and safety

EarthPulse supports situational awareness and research. It does not replace official
emergency alerts, evacuation orders, or professional engineering decisions.
