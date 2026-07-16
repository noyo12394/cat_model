from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.model_card import ModelCard

router = APIRouter(prefix="/models", tags=["models"])

MODEL_CARDS: dict[str, ModelCard] = {
    "event-fusion": ModelCard(
        model_id="event-fusion",
        version="0.2",
        display_name="Event Fusion AI",
        purpose="Group related alerts, forecasts, sensor changes and reports into one evolving incident.",
        method="Deterministic rule-based clustering on time window, geometry proximity, watershed tag and hazard-type relatedness.",
        inputs=["alerts", "forecasts", "sensor observations", "user reports", "watershed tags"],
        outputs=["incident_id", "related_signal_ids", "match_confidence", "explanation"],
        known_limitations=[
            "Not a learned model; thresholds are hand-set and may not generalize to all hazard types.",
            "No natural-language understanding of report text yet - report matching is by structured fields only.",
        ],
        validation_status="Unit-tested against synthetic clustering cases; not yet validated against a large real-event corpus.",
        not_intended_for=["Official incident declaration", "Legal or insurance determinations"],
    ),
    "impact-nowcast": ModelCard(
        model_id="impact-nowcast",
        version="0.3",
        display_name="Impact Nowcasting AI",
        purpose="Estimate possible short-term downstream consequences of an active hazard using official inputs.",
        method="Interpretable rule chain over gauge trend, active alert status, and the infrastructure dependency graph. Never generates its own weather forecast.",
        inputs=["active alerts", "gauge trend", "affected facility list", "dependency graph"],
        outputs=["ordered impact steps with time window, confidence, and evidence"],
        known_limitations=[
            "Confidence bands are heuristic, not calibrated probabilities.",
            "Chain stops at 4 steps; longer cascades are not modeled.",
        ],
        validation_status="No historical calibration performed yet - see docs/MODEL_CARDS.md for the planned replay-based calibration test.",
        not_intended_for=["Official warnings", "Automated public alerting"],
    ),
    "cascade": ModelCard(
        model_id="cascade",
        version="0.1",
        display_name="Living Cascade / dependency propagation",
        purpose="Visualize how a hazard at one facility may propagate through infrastructure dependencies.",
        method="Breadth-first propagation over a NetworkX directed graph with a fixed per-hop time assumption.",
        inputs=["facility list", "infrastructure dependency edges", "hazard-exposed facility ids"],
        outputs=["per-node hop distance, estimated minutes to consequence, narrative"],
        known_limitations=[
            "Per-hop delay (25 minutes) is a single global assumption, not asset-specific.",
            "Dependency graph is seeded/demo data for the Bethlehem corridor only.",
        ],
        validation_status="Not validated against observed cascade timing.",
        not_intended_for=["Engineering-grade outage prediction"],
    ),
    "route-risk": ModelCard(
        model_id="route-risk",
        version="0.2",
        display_name="Route Risk analysis",
        purpose="Characterize hazard exposure along a route between two places.",
        method="Geometric overlap of route segments with alert polygons, plus known crossing attributes (elevation notes, reported closures).",
        inputs=["alert geometry", "route waypoints", "crossing attributes", "reported closures"],
        outputs=["route options with exposure_level, exposure_note, segments"],
        known_limitations=[
            "Only the Lehigh University <-> St. Luke's Bethlehem corridor has a modeled road network; all other pairs get a straight-line low-confidence estimate.",
            "Does not incorporate live traffic.",
        ],
        validation_status="Not validated against ground-truth road closures.",
        not_intended_for=["Claiming a route is safe"],
    ),
    "scenario-engine": ModelCard(
        model_id="scenario-engine",
        version="0.1",
        display_name="Scenario Lab / Counterfactual Action Lab engine",
        purpose="Compute before/after differences for tested infrastructure or response actions.",
        method="Re-runs the cascade and route-risk engines with modified graph state (removed nodes, added edges, response-time adjustments). No LLM computes any number here.",
        inputs=["scenario definition", "action list", "dependency graph", "route network"],
        outputs=["baseline metrics, with-action metrics, delta, assumptions, uncertainty notes"],
        known_limitations=[
            "Action costs are order-of-magnitude planning assumptions.",
            "Only modeled for the seeded Bethlehem scenario in this build.",
        ],
        validation_status="Not validated against real intervention outcomes.",
        not_intended_for=["Financial/insurance-grade loss estimation", "Procurement decisions without expert review"],
    ),
}


@router.get("", response_model=list[ModelCard])
def list_models() -> list[ModelCard]:
    return list(MODEL_CARDS.values())


@router.get("/{model_id}/card", response_model=ModelCard)
def get_model_card(model_id: str) -> ModelCard:
    card = MODEL_CARDS.get(model_id)
    if not card:
        raise HTTPException(status_code=404, detail="Model not found")
    return card
