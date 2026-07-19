"""Product roadmap with owners, budget bands and acceptance gates (deliverable 16).

Budget bands are deliberately coarse (S/M/L/XL) rather than false-precise dollar
figures. Each milestone has an explicit acceptance gate so 'done' is testable.
"""

from __future__ import annotations

from pydantic import BaseModel


class RoadmapMilestone(BaseModel):
    stage: str  # prototype | research_mvp | commercial_mvp | professional | enterprise
    name: str
    owner_role: str
    budget_band: str  # S | M | L | XL (relative effort/cost, not a dollar promise)
    timeline: str
    acceptance_gate: str
    exit_criteria: list[str]
    status: str  # done | in_progress | planned


class RoadmapResponse(BaseModel):
    stages: list[str]
    milestones: list[RoadmapMilestone]
    notice: str


_MILESTONES: list[RoadmapMilestone] = [
    RoadmapMilestone(
        stage="prototype", name="Map-first workspace + labelled demo results",
        owner_role="Full-stack architect", budget_band="M", timeline="Complete",
        acceptance_gate="Search, scenario, map and clearly-labelled demo results usable end to end.",
        exit_criteria=["Map workspace live", "Demo scenario returns labelled ranges", "CAT tooltips present"],
        status="done"),
    RoadmapMilestone(
        stage="research_mvp", name="Flood CAT engine (Lehigh Valley)",
        owner_role="Catastrophe modeller + geospatial engineer", budget_band="L", timeline="Complete",
        acceptance_gate="Deterministic loss chain with uncertainty, provenance and scientific-behaviour tests passing.",
        exit_criteria=["Vulnerability→damage→financial chain", "Monte Carlo uncertainty", "Model auditor", "Tests green"],
        status="done"),
    RoadmapMilestone(
        stage="research_mvp", name="AI copilot (approved tool-calling, no LLM numbers)",
        owner_role="AI/agent architect", budget_band="M", timeline="Complete",
        acceptance_gate="Copilot routes to approved tools; hallucination test proves every number traces to a tool result.",
        exit_criteria=["Provider abstraction", "Tool registry", "Numeric guardrail", "Structured output"],
        status="done"),
    RoadmapMilestone(
        stage="commercial_mvp", name="Durable persistence + background job queue",
        owner_role="Backend + platform engineer", budget_band="L", timeline="Next",
        acceptance_gate="Runs and jobs survive restarts on Postgres/PostGIS + Redis workers with the same API contract.",
        exit_criteria=["PostGIS repository", "Worker queue", "Signed result storage", "Migration from in-memory repo"],
        status="planned"),
    RoadmapMilestone(
        stage="commercial_mvp", name="Live model-vs-reality intelligence",
        owner_role="GIS/remote-sensing + data engineer", budget_band="L", timeline="Next",
        acceptance_gate="Official alerts, sensor/satellite observations and reports compared to the model without altering it automatically.",
        exit_criteria=["Tiered evidence ingestion", "Impact extraction", "Model-mismatch review workflow"],
        status="planned"),
    RoadmapMilestone(
        stage="professional", name="Research pipeline + formula-review workflow",
        owner_role="ML engineer + model reviewer", budget_band="L", timeline="Later",
        acceptance_gate="Live academic-source adapters feed a human review workflow before any formula enters the registry.",
        exit_criteria=["OpenAlex/Crossref/arXiv adapters", "Extraction with human review", "Registry promotion gate"],
        status="planned"),
    RoadmapMilestone(
        stage="professional", name="Additional hazards (wind, quake, wildfire)",
        owner_role="Peril specialists", budget_band="XL", timeline="Later",
        acceptance_gate="Each new peril ships with approved, validated vulnerability functions and its own scientific-behaviour tests.",
        exit_criteria=["Per-peril hazard adapters", "Validated curves", "Multi-hazard scenarios"],
        status="planned"),
    RoadmapMilestone(
        stage="enterprise", name="Tenancy, private models, governance and audit",
        owner_role="Security/privacy + platform lead", budget_band="XL", timeline="Later",
        acceptance_gate="Org isolation, private model registry, role-based approval and full audit logging pass a security review.",
        exit_criteria=["Tenant isolation", "Private registry", "RBAC + approval roles", "Audit logs"],
        status="planned"),
]


def get_roadmap() -> RoadmapResponse:
    return RoadmapResponse(
        stages=["prototype", "research_mvp", "commercial_mvp", "professional", "enterprise"],
        milestones=_MILESTONES,
        notice=(
            "Budget bands are relative effort (S/M/L/XL), not committed dollar figures. "
            "Acceptance gates are the testable definition of done for each milestone."
        ),
    )
