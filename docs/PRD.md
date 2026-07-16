# EarthPulse - Product Requirements Document

## North star

A user can search any place, asset, route or active event and quickly understand:
current hazards, developing conditions, forecast changes, nearby infrastructure,
possible service disruptions, route exposure, historical context, data confidence,
what to monitor next, and what actions could be tested.

The product answers four questions, always in this order: **what is happening**,
**what could happen next**, **who/what could be affected**, **what could reduce the
consequences**.

## Scope of this build

This repository implements the MVP acceptance criteria (all 15 are met - see
"Acceptance criteria" below) for **Phase 1 through Phase 6** of the phased delivery
plan, plus a scoped slice of **Phase 7**:

| Phase | Status | Notes |
|---|---|---|
| 1. Map foundation | Done | MapLibre/OSM by default, Google Maps Platform adapter behind an env var, layer manager, time bar |
| 2. Live data | Done | Typed adapters for NWS, USGS Water, USGS Earthquakes, FIRMS, AirNow, OpenFEMA with demo fallback + Source Health page |
| 3. Location & incidents | Done | Location Capsule, Incident Room, Timeline, What Changed, Evidence Trail |
| 4. Routes & infrastructure | Done | Route Risk, Living Cascade, hospital/bridge/crossing facilities |
| 5. AI | Done | Event Fusion, Impact Nowcasting, Sensor Health, Historical Analog, Grounded Assistant |
| 6. Scenarios | Done | Scenario Lab (simple mode) + Counterfactual Action Lab, sharing one deterministic engine |
| 7. Professional features | Partial | Find Hidden Risks and a CSV-based Portfolio Mode are implemented; Model Comparison, Budget Optimizer, Missing-Data Advisor, and Collaboration are documented as near-term follow-ups (see `KNOWN_LIMITATIONS.md`) |

## Region and hazard focus

Initial region: PA / NJ / NY / DE / MD, with the one seeded, polished demonstration
scenario centered on **Bethlehem, Lehigh Valley, PA** (real places: Lehigh University,
St. Luke's University Hospital - Bethlehem Campus, Lehigh Valley Hospital - Muhlenberg,
the Hill-to-Hill and Fahy bridges, the Lehigh River and Monocacy Creek). Primary hazard:
flooding and heavy rainfall. See `apps/api/app/data/demo/lehigh_valley_flood.py` for the
full honesty note on what in that dataset is real geography vs. synthesized event detail.

## User types

Public, emergency-management, infrastructure/utility, insurance/cat-modeling, and
research users are all addressed by the same UI - see section 4 of the original master
prompt for their distinct needs. This build does not yet implement role-based UI
gating (see `SECURITY.md`); all users currently see the same feature set.

## Acceptance criteria (met by this build)

1. Search a real location - `TopSearchBar` -> `/api/v1/places/search`.
2. View it on a real map - MapLibre/OSM by default; Google Maps Platform when configured.
3. See current alerts and nearby sensors - Location Capsule "Nearby conditions".
4. Click a location and understand current conditions - Location Capsule.
5. Open a real or replayed flood incident - Incident Room, Live and Replay modes.
6. Move through the incident timeline - Incident Room "Timeline" tab + bottom time bar.
7. See what changed - "What Changed?" panel embedded in the Incident Room overview.
8. View a possible short-term impact sequence - "What may happen next" tab.
9. Analyze a route to a hospital - Route Risk panel.
10. Inspect the evidence behind an AI inference - Evidence Trail (expandable on every step).
11. View uncertainty and missing data - Uncertainty Lens toggle + weaknesses in every evidence trail.
12. Run one simple counterfactual scenario - Scenario Lab.
13. Export a readable incident brief - Incident Room "Report" tab (.txt download).
14. Use the product on desktop and mobile - responsive shell (panel moves below the map on narrow viewports).
15. Distinguish observed/forecast/AI-inferred - `CertaintyBadge` styling used throughout.

## Non-goals for this build

- Authentication/RBAC, multi-tenant billing, and production cloud deployment are
  designed for (see `SECURITY.md`, `ARCHITECTURE.md`) but not implemented.
- The knowledge graph (section 31.3) is represented as a NetworkX graph in-process,
  not a persisted, queryable graph database.
- PyTorch/GNN models are not used - the data volume does not justify them yet, per
  the master prompt's own guidance ("add graph neural networks only when sufficient
  validated data exists").
