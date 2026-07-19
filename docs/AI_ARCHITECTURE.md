# RiskChain — AI Architecture (Deliverable 10 / section 13)

The RiskChain copilot is an **AI-native but computation-safe** layer: it
interprets intent, operates approved models, and explains verified results. It
**never computes a number**. Every figure it surfaces is produced by a
deterministic tool and is traceable to that tool's output.

## Flow

```
User message
  → intent inference (mode: ask | explain | analyse | run | research | audit)
  → approved tool selection
  → deterministic backend executes (app/services/cat/*)
  → provider narrates a number-free message
  → numeric guardrail redacts any figure not traceable to a tool result
  → structured, schema-validated response
```

Implemented in `app/services/ai/` and exposed at `POST /copilot/chat`.

## Provider abstraction (`provider.py`)

`NarrationProvider` is a small Protocol; the rest of the platform never depends
on one vendor. `OfflineNarrator` (default, no key, deterministic, number-free)
keeps the product working and tests offline. `GroqNarrator` is the real-provider
seam, used only when `GROQ_API_KEY` is set; its output still passes the numeric
guardrail and falls back to offline text on any error. Anthropic/OpenAI/xAI
adapters slot in behind the same Protocol.

## Tool registry (`tools.py`)

Each tool wraps an approved backend function and returns a **signed structured
result** plus a number-free summary:

| Tool | Wraps | Component |
|------|-------|-----------|
| `run_cat_flood_model` | `services/cat/run.py` | `loss_range_card` |
| `calculate_aal` | `services/cat/probabilistic.py` | `ep_curve` |
| `test_mitigation` | `services/cat/mitigation.py` | `mitigation_comparison` |
| `get_model_card` / `list_models` | `services/cat/model_registry.py` | `model_card` |
| `recommend_model` / `list_vulnerability_functions` | `services/cat/vulnerability.py` | `model_card` / `research_comparison` |
| `audit_model_run` | `services/cat/model_auditor.py` | `data_quality_card` |

Only approved tools are callable; the AI cannot invent a formula or a value.

## Structured output (`schemas/copilot.py`)

The response is a Pydantic-validated `CopilotResponse`: a plain-language
`message`, a `tool_trace` (each call's arguments + structured result),
`components` referencing tool results by id, `map_actions`, `citations`,
`disclaimers`, and `numbers_source` (`approved_tools` | `none`) + `prose_source`
so a client can prove where every figure and sentence came from. The copilot may
only reference approved component types (`GET /copilot/component-catalogue`,
Deliverable 11) — never arbitrary HTML/JS.

## Guardrails (`guardrails.py`)

`redact_unsourced_numbers` scans the narrated message and replaces any number
whose digits do not appear in a tool result with a pointer to the cards. Tests
(`tests/test_copilot.py`) assert the offline prose is number-free, that
unsourced numbers are redacted while sourced ones survive, and — across run /
analyse / mitigation intents — that **every number in the message is traceable
to a tool result**.

## What is still partial

Retrieval over a technical-methods corpus (section 12) and a prompt/evaluation
registry are not built; this layer delivers the provider abstraction, approved
tool-calling gateway, structured-output contract and numeric guardrail.
