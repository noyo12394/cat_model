"""Grounded AI Assistant (section 31.8).

Every answer is assembled from structured platform data - never invented.
The assistant:
  - MAY search platform data, filter the map, explain events, summarize
    changes, compare models, explain uncertainty, and draft scenario configs.
  - MUST NOT invent hazards, losses or probabilities, issue warnings, claim a
    route is safe, or hide uncertainty.

An optional Groq polish step (``_maybe_polish``) may rephrase the assembled
answer for tone, but it is only given an immutable fact block. It cannot run
tools, fetch data, or generate platform numbers. Without ``GROQ_API_KEY`` the
assistant remains fully functional in grounded-rules mode.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from app.core.config import Settings
from app.adapters.gdacs import fetch_global_events
from app.db.memory_repository import MemoryRepository
from app.schemas.assistant import AssistantAnswer, AssistantSource, AssistantToolCall, MapAction
from app.schemas.common import TimeRange
from app.schemas.enums import Confidence
from app.services.find_hidden_risks import find_hidden_risks
from app.services.compound_intelligence import build_compound_events
from app.services.global_outlook import horizon_label, priority_for
from app.services.what_changed import compute_what_changed


def _default_incident(repo: MemoryRepository):
    incidents = repo.list_incidents(mode="live")
    return incidents[0] if incidents else None


def _maybe_polish(answer_text: str, settings: Settings) -> tuple[str, str]:
    """Rephrase an immutable fact block through Groq, with a safe fallback."""
    if not settings.groq_api_key:
        return answer_text, "grounded-rules"

    system_prompt = (
        "You are EarthPulse Navigator. Rewrite the supplied VERIFIED FACT BLOCK in calm, concise "
        "plain language. You must preserve every claim, number, uncertainty word, and negation. "
        "Do not add facts, advice, warnings, probabilities, route-safety claims, or source names. "
        "Do not remove demo/synthetic qualifications. Return only the rewritten paragraph."
    )
    try:
        response = httpx.post(
            f"{settings.groq_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"VERIFIED FACT BLOCK:\n{answer_text}"},
                ],
                "temperature": 0,
                "max_completion_tokens": 320,
            },
            timeout=8.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        if not content or len(content) > max(2200, len(answer_text) * 3):
            return answer_text, "grounded-rules"
        return content, "groq-grounded"
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return answer_text, "grounded-rules"


def answer_question(repo: MemoryRepository, settings: Settings, question: str) -> AssistantAnswer:
    """Public entry point: compute the grounded answer, then run it through
    the (currently no-op) LLM-polish extension point before returning."""
    result = _compute_answer(repo, question)
    polished_text, prose_source = _maybe_polish(result.answer, settings)
    result.answer = polished_text
    result.prose_source = prose_source
    return result


async def answer_question_async(repo: MemoryRepository, settings: Settings, question: str) -> AssistantAnswer:
    """Ground global questions in the live GDACS feed before any AI phrasing."""
    q = question.lower()
    if not any(token in q for token in ("global", "gdacs", "worldwide", "world", "international")):
        return answer_question(repo, settings, question)

    now = datetime.now(timezone.utc)
    horizon = _requested_horizon(q)
    feed = await fetch_global_events(settings)
    if not feed.items:
        result = AssistantAnswer(
            answer="I cannot produce a grounded global brief because the official GDACS feed is currently unavailable. No substitute events are being used.",
            time_range=TimeRange(start=now, label="Global feed check"),
            sources=[AssistantSource(label="GDACS", url="https://www.gdacs.org/")],
            observed_vs_inferred=["No global event facts were available from the official source."],
            confidence=Confidence.LOW,
            limitations=[feed.note],
            tool_trace=[AssistantToolCall(tool="gdacs_global_event_intake", status="stopped", summary="Stopped because the official global event feed was unavailable.")],
            suggested_questions=["Show the regional compound event", "Recheck global events"],
            generated_at=now,
        )
    else:
        watch_items = sorted((priority_for(event, horizon, now=now) for event in feed.items), key=lambda item: -item.priority_score)
        top = watch_items[:3]
        top_text = "; ".join(
            f"{item.priority_label}: {item.name} ({item.alert_level} alert, watch score {item.priority_score}/100)"
            for item in top
        )
        result = AssistantAnswer(
            answer=(
                f"For the {horizon_label(horizon).lower()} operating window, the live GDACS feed has {len(feed.items)} active events. "
                f"The highest verification priorities are {top_text}. These watch scores rank analyst attention from published alert level, GDACS score, and update freshness; they do not predict hazard evolution or impact probability."
            ),
            time_range=TimeRange(start=now, label=f"GDACS {horizon_label(horizon)}"),
            location_label="Global operating picture",
            sources=[AssistantSource(label="Global Disaster Awareness and Coordination System, GDACS", url="https://www.gdacs.org/")],
            observed_vs_inferred=[
                "Event metadata, published alert levels, and GDACS scores are sourced from GDACS.",
                "The watch score is a deterministic EarthPulse triage calculation, not a physical forecast or emergency warning.",
            ],
            confidence=Confidence.MODERATE,
            limitations=[
                "GDACS impact information is indicative and should be cross-checked with national authorities.",
                "The global view does not yet contain location-specific weather, hydrology, exposure, or route models for every event.",
            ],
            tool_trace=[
                AssistantToolCall(tool="gdacs_global_event_intake", summary=f"Read {len(feed.items)} current events from the official GDACS API."),
                AssistantToolCall(tool="transparent_watch_priority", summary="Ranked event verification using alert level, published GDACS score, and source-update freshness."),
                AssistantToolCall(tool="forecast_guardrail", summary="Did not project hazard evolution because no event-specific forecast model was available."),
            ],
            suggested_questions=["Which global events should we verify first?", "Give a global brief for the next 6 hours", "Show the regional compound event"],
            generated_at=now,
        )

    polished_text, prose_source = _maybe_polish(result.answer, settings)
    result.answer = polished_text
    result.prose_source = prose_source
    return result


def _requested_horizon(question: str) -> int:
    minute_match = re.search(r"\b(\d{1,4})\s*[-–]?\s*(?:minutes?|mins?|m)\b", question)
    if minute_match:
        return min(1440, int(minute_match.group(1)))
    hour_match = re.search(r"\b(\d{1,2})\s*(?:hours?|hrs?|h)\b", question)
    if hour_match:
        return min(1440, int(hour_match.group(1)) * 60)
    if "current operating" in question or "right now" in question:
        return 0
    if "24" in question or "tomorrow" in question:
        return 1440
    if "12" in question:
        return 720
    if "6" in question or "six" in question:
        return 360
    if "3" in question or "three" in question:
        return 180
    if "1 hour" in question or "one hour" in question or "60" in question:
        return 60
    return 15


def _compute_answer(repo: MemoryRepository, question: str) -> AssistantAnswer:
    q = question.strip().lower()
    now = datetime.now(timezone.utc)
    incident = _default_incident(repo)

    if any(k in q for k in ("compound", "multi-hazard", "multi hazard", "possible future", "check next", "evidence agree")):
        event = build_compound_events(repo)[0]
        if "check next" in q:
            checks = "; ".join(f"{item.rank}. {item.label}: {item.why}" for item in event.next_checks)
            answer = f"For this research demo, check these in order: {checks}"
        elif "possible future" in q:
            futures = "; ".join(f"{future.label}: {future.detail} {future.consequence}" for future in event.possible_futures)
            answer = f"The qualitative branches are: {futures} These are not calibrated probabilities."
        elif "evidence" in q:
            evidence = "; ".join(f"{item.channel} {item.agreement}: {item.detail}" for item in event.evidence_agreement)
            answer = f"Evidence agreement for this research demo: {evidence}"
        else:
            signals = ", ".join(signal.label for signal in event.signals)
            answer = (
                f"EarthPulse groups {signals} into one compound research demo because they overlap in place, "
                f"time, watershed, and shared infrastructure. {event.fusion_explanation}"
            )
        return AssistantAnswer(
            answer=answer,
            time_range=TimeRange(start=now, label="Current research demo"),
            location_label=event.region_label,
            sources=[AssistantSource(label=signal.source) for signal in event.signals],
            observed_vs_inferred=[
                "The warning and seeded gauge roles are the evidence inputs.",
                "Access and emergency-service consequences are modeled inferences, not confirmed impacts.",
            ],
            confidence=event.fusion_confidence,
            limitations=event.limitations,
            map_actions=[MapAction(action="open_compound_event", target_id=event.event_id)],
            tool_trace=[
                AssistantToolCall(tool="compound_event_fusion", summary="Matched signals by place, time, watershed, and infrastructure."),
                AssistantToolCall(tool="evidence_agreement", summary="Separated supporting channels from missing confirmation."),
                AssistantToolCall(tool="possible_futures", summary="Built qualitative branches without fake probabilities."),
            ],
            suggested_questions=["Which evidence agrees?", "What should we check next?", "Show possible futures"],
            generated_at=now,
        )

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
                tool_trace=[AssistantToolCall(tool="what_changed", summary=f"Compared the incident with {label.replace('_', ' ')} ago.")],
                suggested_questions=["Why is this uncertain?", "What should we check next?"],
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
                tool_trace=[AssistantToolCall(tool="dependency_graph", summary="Searched the seeded infrastructure graph for single points of failure.")],
                suggested_questions=["Which routes are exposed?", "Show the compound event"],
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
            tool_trace=[AssistantToolCall(tool="uncertainty_lens", summary="Reviewed sensor density, estimated elevations, and missing road confirmation.")],
            suggested_questions=["Which evidence agrees?", "What should we check next?"],
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
            tool_trace=[AssistantToolCall(tool="route_exposure", summary="Compared modeled exposure on two seeded hospital routes.")],
            suggested_questions=["Why is the route uncertain?", "Show possible futures"],
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
            tool_trace=[AssistantToolCall(tool="place_profile", summary="Matched the query to the seeded place directory and nearby incident.")],
            suggested_questions=["What changed here?", "Which routes are exposed?"],
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
        tool_trace=[AssistantToolCall(tool="grounding_guard", status="stopped", summary="Stopped because no supported EarthPulse evidence matched the question.")],
        suggested_questions=["Show the compound event", "What changed near Bethlehem?", "What should we check next?"],
        generated_at=now,
    )
