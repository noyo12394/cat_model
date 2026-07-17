# API specification

Full, always-current, generated OpenAPI docs are served by the running backend at
`GET /docs` (Swagger UI) and `GET /openapi.json`. This file is a stable, human-readable
index of the endpoints and what each one is for.

Base path: `/api/v1`. All responses are JSON. See `docs/DATA_SOURCE_CARDS.md` for what
backs each endpoint's data, and `apps/api/app/schemas/` for the exact response shapes.

| Endpoint | Method | Purpose |
|---|---|---|
| `/live/events` | GET | Raw current events/alerts/sensors feed |
| `/live/global-events` | GET | Normalized live GDACS global multi-hazard event feed with alert levels, provenance and freshness |
| `/live/global-outlook?horizon_minutes=0..1440` | GET | Transparent global verification-priority queue derived from current GDACS alert level, score and freshness; explicitly not a physical hazard forecast |
| `/live/multi-hazard` | GET | Research-demo compound-event fusion, evidence agreement and possible futures |
| `/live/summary` | GET | Regional summary (default right-panel content) |
| `/places/search?q=` | GET | Place/facility search (powers the top search bar) |
| `/places/{place_id}` | GET | Basic place record |
| `/places/{place_id}/capsule` | GET | Location Capsule |
| `/places/{place_id}/conditions` | GET | Alias of `/capsule` (section 36 naming) |
| `/places/{place_id}/history` | GET | Historical note (stub beyond the seeded replay) |
| `/incidents?mode=live\|replay` | GET | List incidents |
| `/incidents/{id}?mode=` | GET | Incident detail |
| `/incidents/{id}/timeline?mode=` | GET | Timeline entries |
| `/incidents/{id}/forecast?mode=` | GET | "What may happen next" impact sequence |
| `/incidents/{id}/impacts?mode=` | GET | Living Cascade (dependency propagation graph) |
| `/incidents/{id}/evidence?mode=` | GET | Full evidence trail list |
| `/incidents/{id}/what-changed?mode=&compared_to=` | GET | What Changed? diff |
| `/incidents/{id}/analogs` | GET | Historical Analog Finder results |
| `/routes/analyze` | POST | Route Risk analysis between two place ids |
| `/scenarios` | POST | Create a scenario configuration |
| `/scenarios/{id}/run` | POST | Run the Scenario/Counterfactual engine |
| `/scenarios/{id}/results` | GET | Fetch a previously computed result |
| `/portfolio/upload` | POST | CSV asset upload + validation + exposure |
| `/portfolio/{id}/exposure` | GET | Re-fetch a portfolio's exposure summary |
| `/assistant/query` | POST | Grounded AI Assistant |
| `/sources/status` | GET | Source Health page data |
| `/models` | GET | All model cards |
| `/models/{model_id}/card` | GET | One model card |
| `/risks/hidden` | GET | Find Hidden Risks ranked list |
| `/community/pulse?incident_id=` | GET | Community Pulse sentiment analysis: deterministic concern index (weighted count of categorical sentiment tags), theme clusters, and corroborated-vs-rumor cross-check over `user_reported`/`unverified` community reports |

## Conventions

- `mode` query params are `live` (default) or `replay`.
- Every record includes a certainty/status signal - `certainty_class` on
  events/timeline entries, `data_status` inside `provenance`, or `confidence` on
  AI-derived outputs. The frontend renders these with distinct visual styles
  (`apps/web/src/components/common/Badges.tsx`) and never presents an AI inference as
  an official warning.
- Errors are plain `{"detail": "..."}` JSON with a standard HTTP status code; there is
  no bespoke error envelope.
