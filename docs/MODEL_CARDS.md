# Model cards

Live, machine-readable versions of these cards are served at `GET /api/v1/models` and
`GET /api/v1/models/{model_id}/card` (source: `apps/api/app/api/v1/models.py`). This
file mirrors them for offline reading; if the two ever disagree, the API response is
authoritative.

## event-fusion (v0.2)

- **Purpose:** group related alerts, forecasts, sensor changes and reports into one
  evolving incident.
- **Method:** deterministic rule-based clustering on time window, geometry proximity,
  watershed tag, and hazard-type relatedness.
- **Known limitations:** thresholds are hand-set, not learned; no NLP over report text.
- **Not intended for:** official incident declaration, legal/insurance determinations.

## impact-nowcast (v0.3)

- **Purpose:** estimate possible short-term downstream consequences of an active
  hazard using official inputs.
- **Method:** interpretable rule chain over gauge trend, active alert status, and the
  infrastructure dependency graph. Never generates its own weather forecast.
- **Known limitations:** confidence bands are heuristic, not calibrated probabilities;
  the chain stops at 4 steps.
- **Not intended for:** official warnings, automated public alerting.

## cascade (v0.1)

- **Purpose:** visualize how a hazard at one facility may propagate through
  infrastructure dependencies.
- **Method:** breadth-first propagation over a NetworkX directed graph with a fixed
  per-hop time assumption (25 minutes).
- **Known limitations:** per-hop delay is a single global assumption, not
  asset-specific; the dependency graph is seeded/demo data for one corridor.
- **Not intended for:** engineering-grade outage prediction.

## route-risk (v0.2)

- **Purpose:** characterize hazard exposure along a route between two places.
- **Method:** geometric overlap of route segments with alert polygons, plus known
  crossing attributes (elevation notes, reported closures).
- **Known limitations:** only one corridor (Lehigh University <-> St. Luke's Bethlehem)
  has a modeled road network; all other place pairs get a straight-line, low-confidence
  estimate; no live traffic.
- **Not intended for:** claiming a route is safe.

## scenario-engine (v0.1)

- **Purpose:** compute before/after differences for tested infrastructure or response
  actions (Scenario Lab + Counterfactual Action Lab).
- **Method:** re-runs the cascade and route-risk engines with modified graph state.
  No LLM computes any number here.
- **Known limitations:** action costs are order-of-magnitude planning assumptions;
  only modeled for the seeded Bethlehem scenario.
- **Not intended for:** financial/insurance-grade loss estimation, procurement
  decisions without expert review.

## grounded-assistant (unversioned, rule-based)

- **Purpose:** answer natural-language questions using only structured platform data.
- **Method:** keyword-routed templates over the same repository every other feature
  reads from; every answer includes time range, location, sources, observed-vs-inferred
  labels, confidence, and limitations.
- **Known limitations:** intent coverage is a small, hand-written set (what-changed,
  hidden-risk, uncertainty, route/hospital, place-lookup, fallback); not a general
  question-answering system.
- **Not intended for:** issuing warnings, claiming safety, or answering questions
  outside the seeded demo region's data.
