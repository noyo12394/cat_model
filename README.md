# EarthPulse

A live intelligence platform for hazards, infrastructure and community impacts. Map-first
situational awareness that connects a developing hazard to real places, routes, and
infrastructure dependencies - while keeping every AI conclusion traceable to evidence.

This repository is the first functioning build: a working FastAPI backend and Next.js
frontend, seeded with one polished demonstration scenario (a developing flood near
Bethlehem, PA / Lehigh Valley), following the phased scope in `docs/PRD.md`.

**Start here:**

- [`docs/PRD.md`](docs/PRD.md) - product requirements and what "done" means for this build
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - system design and key decisions
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) - what is real vs. scoped out, and why

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

Every external data source (NWS, USGS Water, USGS Earthquakes, NASA FIRMS, AirNow,
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
