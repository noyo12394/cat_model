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
| `/sources/registry` | GET | Governed source matrix: access, licence summary, update cadence, resolution, attribution, fallback and quality notes |
| `/models` | GET | All model cards |
| `/models/{model_id}/card` | GET | One model card |
| `/risks/hidden` | GET | Find Hidden Risks ranked list |
| `/community/pulse?incident_id=` | GET | Community Pulse sentiment analysis: deterministic concern index (weighted count of categorical sentiment tags), theme clusters, and corroborated-vs-rumor cross-check over `user_reported`/`unverified` community reports |
| `/cat/exposure/demo` | GET | Demonstration exposure assets with per-attribute origin flags |
| `/cat/vulnerability-functions` | GET | Depth-damage curves (experimental) with calibration ranges |
| `/cat/models` | GET | CAT model registry (cards + approval status) |
| `/cat/models/{model_id}` | GET | One model card |
| `/cat/mitigation-options` | GET | Available mitigation interventions |
| `/cat/jobs` | POST | Queue-compatible run submission; the public demo truthfully reports `inline_demo` execution |
| `/cat/jobs/{id}` | GET | Job state, progress, run link and runtime limitations |
| `/cat/jobs/{id}/result` | GET | Completed immutable result or a conflict response while incomplete |
| `/cat/model-runs` | POST | Run the full deterministic flood loss chain; returns immutable run + manifest |
| `/cat/model-runs` | GET | List run summaries |
| `/cat/model-runs/{id}` | GET | Full run result (damage, financial, audit, confidence, sources, limitations) |
| `/cat/model-runs/{id}/uncertainty` | GET | Ground-up / gross / net loss distributions + confidence |
| `/cat/model-runs/{id}/manifest` | GET | Exact reproducibility manifest |
| `/cat/model-runs/{id}/audit` | GET | Model-auditor findings and limitations |
| `/cat/model-runs/{id}/layers` | GET | Available result-layer catalogue |
| `/cat/model-runs/{id}/layers/{layer_id}` | GET | GeoJSON derived from that immutable run's asset results |
| `/cat/model-runs/{id}/compare?comparison_run_id=` | POST | Recorded-output and changed-assumption comparison; no hidden recalculation |
| `/cat/model-runs/{id}/reports?report_type=` | POST | Structured executive, technical, underwriting or public report with manifest and citations |
| `/cat/model-runs/{id}/probabilistic?years=&seed=` | GET | Event-set AAL / OEP / AEP / VaR / TVaR anchored to the run |
| `/cat/model-runs/{id}/mitigation?option_id=` | POST | Avoided-loss comparison for one intervention |
| `/cat/data-coverage` | GET | Layer-by-layer availability, origin, resolution, use and limitations |
| `/cat/capabilities` | GET | Truthful 16-deliverable implementation audit for the current release |
| `/copilot/chat` | POST | CAT copilot: interprets intent, runs approved tools, narrates verified results; no number comes from the LLM (`numbers_source`/`prose_source` prove provenance) |
| `/copilot/tools` | GET | Approved tool registry the copilot may call |
| `/copilot/component-catalogue` | GET | Approved frontend components the copilot may reference (deliverable 11) |

See `docs/CAT_MODEL_SPEC.md` for the scientific specification. Every CAT result
is `data_status: demo`; losses are ranges, not single values; no LLM computes
any number.

The public deployment intentionally uses an in-process demonstration repository.
Its job records are queue-compatible but not durable across serverless cold starts;
the returned `execution_mode` and limitations make that boundary machine-readable.

## Conventions

- `mode` query params are `live` (default) or `replay`.
- Every record includes a certainty/status signal - `certainty_class` on
  events/timeline entries, `data_status` inside `provenance`, or `confidence` on
  AI-derived outputs. The frontend renders these with distinct visual styles
  (`apps/web/src/components/common/Badges.tsx`) and never presents an AI inference as
  an official warning.
- Errors are plain `{"detail": "..."}` JSON with a standard HTTP status code; there is
  no bespoke error envelope.
