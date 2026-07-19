"""Copilot tests (section 13, non-negotiable 4 + AI hallucination tests).

The load-bearing guarantee: no numeric figure in the copilot's prose comes from
the language model. These tests assert routing, structured output, and the
numeric guardrail directly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.memory_repository import MemoryRepository
from app.main import app
from app.schemas.copilot import AiContext, CopilotMode, CopilotRequest
from app.services.ai.guardrails import find_numbers, redact_unsourced_numbers
from app.services.ai.orchestrator import answer
from app.services.ai.provider import OfflineNarrator, get_provider


def _answer(message: str, mode: CopilotMode | None = None):
    return answer(CopilotRequest(message=message, mode=mode, context=AiContext()),
                  MemoryRepository(), Settings())


# --- Guardrail ---------------------------------------------------------------

def test_offline_provider_prose_contains_no_numbers():
    narrator = OfflineNarrator()
    text = narrator.narrate("run", "run a flood loss", ["I ran the approved flood loss chain."])
    assert find_numbers(text) == []


def test_redaction_removes_unsourced_numbers_but_keeps_sourced_ones():
    tool_results = [{"aal_usd": 913180, "p50_usd": 3200000}]
    msg = "The AAL is 913180 but a made-up figure 8675309 should be removed."
    cleaned, had_unsourced = redact_unsourced_numbers(msg, tool_results)
    assert had_unsourced is True
    assert "913180" in cleaned          # traceable to a tool result -> kept
    assert "8675309" not in cleaned     # unsourced -> redacted


def test_default_provider_is_offline_without_key():
    assert get_provider(Settings()).name == "offline-deterministic"


# --- Routing + structured output ---------------------------------------------

def test_run_request_routes_to_flood_model_and_returns_loss_component():
    resp = _answer("Run a 100-year flood loss for Bethlehem")
    assert resp.mode == CopilotMode.RUN
    tools_used = [tc.tool for tc in resp.tool_trace]
    assert "run_cat_flood_model" in tools_used
    assert any(c.type == "loss_range_card" for c in resp.components)
    assert resp.numbers_source == "approved_tools"


def test_analyse_request_computes_aal_via_tool():
    resp = _answer("What is the AAL and the AEP curve?")
    assert "calculate_aal" in [tc.tool for tc in resp.tool_trace]
    assert any(c.type == "ep_curve" for c in resp.components)


def test_mitigation_request_runs_baseline_and_mitigation():
    resp = _answer("How can we reduce the loss by elevating homes?")
    tools_used = [tc.tool for tc in resp.tool_trace]
    assert "test_mitigation" in tools_used


def test_audit_request_returns_findings():
    resp = _answer("Audit this run - what might be missing or double counted?")
    assert resp.mode == CopilotMode.AUDIT
    assert "audit_model_run" in [tc.tool for tc in resp.tool_trace]


def test_conceptual_question_uses_glossary_and_no_tools():
    resp = _answer("What is secondary uncertainty?")
    assert resp.tool_trace == [] or all(tc.result is None for tc in resp.tool_trace)
    assert any(c.source_id.startswith("glossary:") for c in resp.citations)
    # A conceptual answer must still be number-free.
    assert find_numbers(resp.message) == []


def test_every_number_in_message_is_traceable_to_a_tool_result():
    """The core hallucination test across several intents."""
    for msg in ["Run the flood scenario", "Show me the AAL", "Reduce loss with floodproofing"]:
        resp = _answer(msg)
        pool = "".join(ch for tc in resp.tool_trace if tc.result for ch in str(tc.result) if ch.isdigit())
        for token in find_numbers(resp.message):
            digits = "".join(ch for ch in token if ch.isdigit())
            assert digits in pool, f"Unsourced number {token!r} in message for {msg!r}"


# --- API ---------------------------------------------------------------------

def test_chat_endpoint_and_catalogue():
    client = TestClient(app)
    r = client.post("/api/v1/copilot/chat", json={"message": "Run a flood loss analysis"})
    assert r.status_code == 200
    body = r.json()
    assert body["numbers_source"] in ("approved_tools", "none")
    assert body["prose_source"] == "offline-deterministic"
    assert client.get("/api/v1/copilot/tools").status_code == 200
    cat = client.get("/api/v1/copilot/component-catalogue")
    assert cat.status_code == 200 and len(cat.json()) >= 5
