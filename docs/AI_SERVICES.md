# AI service definitions

Maps each AI system from the master prompt (section 31) to its implementation and
honest status in this build.

| System | Implementation | Status |
|---|---|---|
| 31.1 Event Fusion AI | `services/event_fusion.py` - deterministic clustering on hazard-type relatedness, time window, geometric proximity and watershed tag; every incident's `fusion_reason` cites which factors matched | Implemented |
| 31.2 Impact Nowcasting AI | `services/impact_nowcast.py` - interpretable rule chain over active alerts + gauge trend + the dependency graph; never generates its own weather forecast; confidence explicitly decreases with each inferential hop | Implemented |
| 31.3 Catastrophe Knowledge Graph | `services/cascade.py` builds a NetworkX `DiGraph` from `facilities` + `infrastructure_dependencies` at request time | Implemented as an in-process graph; not yet a persisted, independently queryable graph database |
| 31.4 Historical Analog AI | `services/historical_analog.py` + seeded `HistoricalAnalog` records with a similarity-scoring function (`score_similarity`) | Implemented against seeded/synthetic composites; not yet wired to a real historical event corpus |
| 31.5 Sensor Health AI | `services/sensor_health.py` - detects frozen, jumpy, and stale sensors from the observation series | Implemented |
| 31.6 Evidence Extraction AI | N/A | Not implemented - no free-text official bulletins are ingested in this build (NWS alert `description` fields are used verbatim, not NLP-extracted) |
| 31.7 Image Understanding AI | N/A | Not implemented - no imagery pipeline in this build; would sit behind the Before/After view (section 19), not yet built |
| 31.8 Grounded AI Assistant | `services/assistant.py` - routes questions through deterministic EarthPulse tools, exposes a tool trace, then optionally uses Groq to rephrase the immutable fact block; every answer includes time range, location, sources, observed-vs-inferred labels, confidence, and limitations | Implemented; works in grounded-rules mode with optional Groq phrasing |

## The "no LLM for numbers" rule, concretely

`services/scenario_engine.py`, `services/cascade.py`, and `services/route_risk.py`
compute every number (affected population, travel time, emergency response time,
action cost) via NetworkX graph algorithms, geometric overlap checks, and explicit,
labeled assumption constants (e.g. `BASELINE_EMERGENCY_RESPONSE_MINUTES = 12.0`). None
of it passes through a language model. `ScenarioResult.method` states this directly in
the API response itself, not just in documentation.

## Where a real LLM would plug in

`services/assistant.py` has a single, constrained extension point (`_maybe_polish`).
When `GROQ_API_KEY` is configured it sends only the assembled, fact-checked answer to
Groq's OpenAI-compatible Chat Completions endpoint. Groq cannot call EarthPulse tools
or add a fact, number, probability, source, or route-safety claim. API failure falls
back to the unchanged grounded response.
