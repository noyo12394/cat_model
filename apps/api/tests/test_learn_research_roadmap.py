"""Tests for Learn CAT (14), Research (12) and Roadmap (16)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.learn import LESSONS, get_lesson, list_lessons
from app.services.research import CURATED_INDEX, request_extraction, search
from app.services.roadmap import get_roadmap

client = TestClient(app)


# --- Learn CAT ---------------------------------------------------------------

def test_every_lesson_has_the_required_teaching_fields():
    for lesson in LESSONS:
        assert lesson.one_sentence and lesson.plain_language and lesson.technical_definition
        assert lesson.interactive_example and lesson.common_mistake and lesson.real_world_use
        assert lesson.knowledge_check.options and 0 <= lesson.knowledge_check.answer_index < len(lesson.knowledge_check.options)


def test_lessons_are_ordered_and_addressable():
    summaries = list_lessons()
    assert [s.order for s in summaries] == sorted(s.order for s in summaries)
    first = summaries[0]
    assert get_lesson(first.lesson_id) is not None


def test_learn_endpoints():
    assert client.get("/api/v1/learn/lessons").status_code == 200
    assert client.get("/api/v1/learn/lessons/aal").status_code == 200
    assert client.get("/api/v1/learn/lessons/nope").status_code == 404
    assert client.get("/api/v1/learn/glossary").status_code == 200
    assert client.get("/api/v1/learn/glossary/AAL").status_code == 200


# --- Research ----------------------------------------------------------------

def test_search_ranks_and_never_marks_papers_extracted_by_default():
    resp = search("flood vulnerability functions for commercial buildings", hazard="flood", asset_type="commercial")
    assert resp.results
    assert resp.results == sorted(resp.results, key=lambda r: r.relevance, reverse=True)
    for paper in CURATED_INDEX:
        assert paper.extraction_performed is False
        assert paper.human_review_status.value == "discovered"


def test_extraction_opens_review_and_never_promotes_a_formula():
    result = request_extraction("fema-hazus-flood-tm")
    assert result is not None
    assert result.new_status.value == "under_review"
    assert result.new_status.value != "approved_for_production"
    assert any("review" in step.lower() for step in result.workflow)


def test_research_endpoints_and_honest_source_status():
    r = client.post("/api/v1/research/search", json={"query": "depth-damage residential flood"})
    assert r.status_code == 200
    body = r.json()
    # Live academic sources are truthfully reported as unavailable, not faked.
    assert any(s["status"] == "unavailable" for s in body["source_status"])
    assert any(s["status"] == "demo_index" for s in body["source_status"])
    assert client.get("/api/v1/research/papers/usace-egm-residential-depth-damage").status_code == 200
    assert client.get("/api/v1/research/papers/nope").status_code == 404
    assert client.post("/api/v1/research/papers/fema-hazus-flood-tm/extract").status_code == 200


# --- Roadmap -----------------------------------------------------------------

def test_roadmap_milestones_have_owners_budgets_and_acceptance_gates():
    roadmap = get_roadmap()
    assert roadmap.milestones
    for m in roadmap.milestones:
        assert m.owner_role and m.budget_band and m.acceptance_gate
        assert m.exit_criteria
        assert m.stage in roadmap.stages


def test_roadmap_endpoint():
    r = client.get("/api/v1/roadmap")
    assert r.status_code == 200 and len(r.json()["milestones"]) >= 5
