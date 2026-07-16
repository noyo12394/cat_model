# Test plan

## What exists today

**Backend unit/integration tests** (`apps/api/tests/`, run with `pytest`, 46 tests):

- `test_geo.py` - haversine distance, point-in-polygon, segment/polygon intersection.
- `test_confidence.py` - score-to-band mapping, staleness-driven confidence downgrade.
- `test_event_fusion.py` - signal clustering by hazard relatedness/time/geometry,
  including a check that the seeded incident's own signals would cluster under the
  general-purpose algorithm (not just its canned narrative).
- `test_route_risk.py` - all three exposure states present, no route ever positively
  labeled "safe", unknown place pairs return no options, generic pairs fall back to a
  low-confidence estimate.
- `test_cascade.py` - hop-distance propagation, node removal, unaffected nodes.
- `test_scenario_engine.py` - zero-action scenarios produce zero delta; closing a
  crossing early does not silently zero out population exposure; travel time is never
  negative; the result documents that no LLM computed a number.
- `test_sensor_health.py` - seeded data has no false frozen/jump flags; a synthetic
  frozen series is correctly detected.
- `test_what_changed.py` - gauge deltas, full-timeline "yesterday" comparison, unknown
  incident handling, closure-status always reported.
- `test_schemas.py` - Pydantic validation (rejects malformed geometry, normalizes a
  sensor observation).
- `test_api_integration.py` - FastAPI `TestClient` end-to-end: search -> capsule,
  incident -> timeline/forecast/evidence, route analysis, full scenario create/run/
  fetch lifecycle (including the 404-before-run case), assistant query shape, hidden
  risks ranking, source health listing, model card 404.

Run: `cd apps/api && source .venv/bin/activate && python -m pytest`

**Frontend**: `npm run build` (typecheck + production build) and `npm run lint`
(ESLint) both pass clean - see `apps/web/package.json`. No frontend unit/E2E test
suite is wired up yet (see gaps below).

**Manual verification performed for this build** (see PR description for screenshots):
search -> Location Capsule -> Incident Room (all tabs) -> Route Risk -> Scenario Lab
(run with actions) -> Grounded Assistant -> Replay mode with dark color scheme -> mobile
viewport. No console errors were observed other than expected OpenStreetMap tile
fetches failing in the sandboxed test environment (no outbound access to
`tile.openstreetmap.org`), which the map degrades from gracefully (markers/panels are
unaffected).

## Gaps (honest, not yet done)

- **Frontend unit tests** (component-level, e.g. with Vitest/React Testing Library):
  not set up.
- **End-to-end browser tests** (Playwright): not automated into a repeatable suite -
  the manual pass above was done ad hoc during development, not committed as a test
  file.
- **Visual regression tests**: not set up.
- **Model validation tests** (calibration, geographic/temporal holdout, false-alert
  analysis): not applicable yet in a meaningful way - the rule-based models here don't
  have learned parameters to calibrate, and there is no historical corpus loaded to
  hold out. This becomes relevant once `impact_nowcast.py`'s thresholds are replaced
  with anything learned from real data.
- **Load/performance testing**: not performed. The 50,000-feature clustering
  requirement (section 43) is unexercised at the current seeded-data scale (a
  handful of facilities/sensors).

## Recommended next additions, in priority order

1. Playwright E2E covering the MVP acceptance-criteria flow (already manually verified
   once - see above) as a committed, CI-runnable test.
2. Vitest + React Testing Library for `Badges.tsx`, `EvidenceTrailView.tsx`, and the
   Zustand store's mode/panel transitions.
3. A `pip-audit`/`npm audit` CI gate (dependency scanning, section 40).
