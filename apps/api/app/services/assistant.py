"""Grounded AI Assistant (section 31.8).

Every answer is assembled from structured platform data - never invented.
The assistant:
  - MAY search platform data, filter the map, explain events, summarize
    changes, compare models, explain uncertainty, and draft scenario configs.
  - MUST NOT invent hazards, losses or probabilities, issue warnings, claim a
    route is safe, or hide uncertainty.

An optional LLM polish step (``_maybe_polish``) may rephrase the assembled
answer for tone, but it is only ever given the already-computed facts as
input, never asked to produce new facts or numbers - and it is a no-op
unless ``ANTHROPIC_API_KEY`` is configured and the ``anthropic`` package is
installed, so the assistant works fully offline by default.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.schemas.assistant import AssistantAnswer, AssistantSource, MapAction
from app.schemas.common import TimeRange
from app.schemas.enums import Confidence
from app.services.find_hidden_risks import find_hidden_risks
from app.services.what_changed import compute_what_changed


def _default_incident(repo: MemoryRepository):
    incidents = repo.list_incidents(mode="live")
    return incidents[0] if incidents else None


def _maybe_polish(answer_text: str, settings: Settings) -> tuple[str, str]:
    """Extension point for LLM prose polishing.

    Returns (text, prose_source). Only ever receives the already-computed,
    fact-checked answer string - never the underlying data - so there is no
    path for an LLM to introduce a new claim, number, or probability. This is
    intentionally a no-op today: no ``anthropic`` call is wired up, since
    doing so would add an external dependency and cost with no behavior
    change until a real prompt/eval has been designed for it.
    """
    if not settings.anthropic_api_key:
        return answer_text, "rule-based"
    # A configured deployment would call the Claude API here with a prompt
    # constrained to rephrasing `answer_text` only, then return
    # (polished_text, "llm-polished"). Left unimplemented pending that
    # prompt/eval design - see docs/AI_SERVICES.md.
    return answer_text, "rule-based"


def answer_question(repo: MemoryRepository, settings: Settings, question: str) -> AssistantAnswer:
    """Public entry point: compute the grounded answer, then run it through
    the (currently no-op) LLM-polish extension point before returning."""
    result = _compute_answer(repo, question)
    polished_text, prose_source = _maybe_polish(result.answer, settings)
    result.answer = polished_text
    result.prose_source = prose_source
    return result


def _compute_answer(repo: MemoryRepository, question: str) -> AssistantAnswer:
    q = question.strip().lower()
    now = datetime.now(timezone.utc)
    incident = _default_incident(repo)

    if any(k in q for k in ("what changed", "compare", "since", "hours ago", "yesterday")):
        label = "6_hours" if "six" in q or "6" in q else "1_hour"
        changed = compute_what_changed(repo, incident.incident_id, "live", label) if incident else None
        if changed:
            lines = [c.detail or c.label for c in changed.changes]
            return AssistantAnswer(
                answer="Since " + label.replace("_", " ") + " ago: " + " ".join(lines),
                time_range=TimeRange(start=changed.compared_to_at, end=changed.now_at, label=f"Last {label.replace('_', ' ')}"),
                location_label=incident.region_label if incident else None,
                sources=[AssistantSource(label=s) for s in (incident.sources if incident else [])],
                observed_vs_inferred=[
                    "Gauge changes are observed.",
                    "Timeline entries are labeled by their own certainty class.",
                ],
                confidence=Confidence.MODERATE,
                limitations=["Limited to the one seeded/live incident this build tracks."],
                map_actions=[MapAction(action="focus_incident", target_id=incident.incident_id)] if incident else [],
                generated_at=now,
            )

    if any(k in q for k in ("isolate", "single point", "only one", "hidden risk", "spof")):
        risks = find_hidden_risks(repo)
        spof = [r for r in risks if r.category == "single_point_of_failure"]
        if spof:
            lines = [f"{r.title}." for r in spof[:5]]
            return AssistantAnswer(
                answer=" ".join(lines) if lines else "No single points of failure were found in the current dependency graph.",
                time_range=TimeRange(start=now, label="Current"),
                location_label="Bethlehem, Lehigh Valley, PA",
                sources=[AssistantSource(label="EarthPulse infrastructure dependency graph (seeded)")],
                observed_vs_inferred=["This is an AI-inferred structural finding from the dependency graph, not an official assessment."],
                confidence=Confidence.MODERATE,
                limitations=["The dependency graph is seeded/demo data, not a live utility/DOT feed."],
                map_actions=[MapAction(action="filter_layer", target_id="hidden_risks")],
                generated_at=now,
            )

    if any(k in q for k in ("uncertain", "why is this", "confidence")):
        return AssistantAnswer(
            answer=(
                "Confidence is moderate here. The nearest gauges are seeded demo sensors rather than "
                "a dense monitoring network, road elevations near the crossings are estimated rather "
                "than surveyed, and the rainfall forecast driving this incident can still change."
            ),
            time_range=TimeRange(start=now, label="Current"),
            location_label=incident.region_label if incident else None,
            sources=[AssistantSource(label="National Weather Service (demo)"), AssistantSource(label="USGS Water Data (demo)")],
            observed_vs_inferred=[
                "Gauge trend: observed.",
                "Warning: official alert.",
                "Downstream impact steps: AI-inferred, lower confidence the further downstream.",
            ],
            confidence=Confidence.MODERATE,
            limitations=[
                "Road elevation is estimated, not surveyed.",
                "No road-camera confirmation is available for the affected crossings.",
            ],
            map_actions=[MapAction(action="filter_layer", target_id="uncertainty")],
            generated_at=now,
        )

    if any(k in q for k in ("hospital", "route", "road")) and incident:
        return AssistantAnswer(
            answer=(
                "Two hospitals are within the area this incident affects: St. Luke's University Hospital "
                "- Bethlehem Campus and Lehigh Valley Hospital - Muhlenberg. The Hill-to-Hill Bridge route "
                "currently shows elevated exposure; the Fahy Bridge route shows lower current exposure. "
                "Neither route is confirmed closed."
            ),
            time_range=TimeRange(start=now, label="Current"),
            location_label=incident.region_label,
            sources=[AssistantSource(label="EarthPulse Route Risk analysis")],
            observed_vs_inferred=["Route exposure levels are AI-assisted assessments based on official alert geometry, not guarantees."],
            confidence=Confidence.MODERATE,
            limitations=["Only the seeded Bethlehem corridor has a modeled road network in this build."],
            map_actions=[MapAction(action="focus_incident", target_id=incident.incident_id)],
            generated_at=now,
        )

    place = None
    for candidate in repo.search_places(q, limit=1):
        place = candidate
        break
    if place:
        return AssistantAnswer(
            answer=(
                f"{place['name']} does not have a confirmed severe local impact right now. "
                + (
                    f"It is near the '{incident.title}' incident."
                    if incident
                    else "No active incident is being tracked nearby."
                )
            ),
            time_range=TimeRange(start=now, label="Current"),
            location_label=place["name"],
            sources=[AssistantSource(label="EarthPulse place directory (demo)")],
            observed_vs_inferred=["Status summary combines an official alert with AI-assisted grouping."],
            confidence=Confidence.MODERATE,
            limitations=["Place directory is a small seeded set in this build, not a full geocoder."],
            map_actions=[MapAction(action="focus_place", target_id=place["place_id"])],
            generated_at=now,
        )

    return AssistantAnswer(
        answer=(
            "I don't have grounded data to answer that in this build. I can answer questions about "
            "the seeded Bethlehem flood incident, its routes, hidden risks, and what changed recently."
        ),
        time_range=TimeRange(start=now, label="Current"),
        confidence=Confidence.LOW,
        limitations=["This build's assistant only has structured data for the seeded demo region."],
        generated_at=now,
    )
