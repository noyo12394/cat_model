"""RiskChain AI copilot schemas (master prompt section 13, deliverable 10).

The copilot is provider-agnostic and, crucially, **never computes a number**.
It interprets intent, calls approved deterministic tools, and narrates the
verified results. The response shape mirrors section 13's structured-output
contract: a plain-language ``message`` plus ``components`` and ``map_actions``
that reference tool results by id, plus ``citations`` and explicit
``numbers_source`` provenance so a client can prove no figure came from the LLM.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CopilotMode(str, Enum):
    ASK = "ask"          # general CAT-modelling questions
    EXPLAIN = "explain"  # explain a result or interface item
    ANALYSE = "analyse"  # interrogate the current scenario
    RUN = "run"          # operate approved modelling tools
    RESEARCH = "research"  # search technical methods (metadata only)
    AUDIT = "audit"      # challenge the current model


class AiContext(BaseModel):
    """Structured context sent to the copilot (section 13). Deliberately small:
    private portfolio detail is never required here."""

    user_role: str = "learner"
    interface_mode: str = "guided"  # guided | professional
    hazard: str | None = None
    location_label: str | None = None
    run_id: str | None = None
    permissions: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    id: str
    tool: str
    arguments: dict[str, Any]
    status: str  # ok | error | skipped
    summary: str
    result: dict[str, Any] | None = None  # signed, structured tool output


class CopilotComponent(BaseModel):
    type: str  # approved component type (see component catalogue)
    title: str
    data_reference: str  # id of the ToolCall whose result feeds this component


class MapActionSpec(BaseModel):
    action: str
    target_ids: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    source_id: str
    label: str | None = None
    url: str | None = None


class CopilotResponse(BaseModel):
    response_type: str
    mode: CopilotMode
    message: str
    tool_trace: list[ToolCall]
    components: list[CopilotComponent]
    map_actions: list[MapActionSpec]
    citations: list[Citation]
    disclaimers: list[str]
    # Provenance of every number in this response.
    numbers_source: str  # "approved_tools" | "none"
    prose_source: str    # which narrator produced the message
    generated_at: datetime


class CopilotRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    mode: CopilotMode | None = None  # inferred if omitted
    context: AiContext = Field(default_factory=AiContext)


class ToolDescriptor(BaseModel):
    name: str
    description: str
    approved: bool
    computes_numbers: bool
    output_component: str | None = None


class ComponentCatalogueEntry(BaseModel):
    """Deliverable 11: an approved frontend component and the data it consumes.
    The AI may only reference these types; it cannot emit arbitrary HTML/JS."""

    type: str
    purpose: str
    consumes: str
