"""Living Cascade schema (section 14)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CascadeNode(BaseModel):
    facility_id: str
    name: str
    facility_type: str
    operational_state: str
    served_population: int = 0
    directly_exposed: bool = False
    hops_from_hazard: int | None = None
    estimated_minutes_to_consequence: float | None = None
    is_removed: bool = False


class CascadeEdge(BaseModel):
    from_facility_id: str
    to_facility_id: str
    relationship: str
    strength: float
    is_uncertain: bool = False


class CascadeResult(BaseModel):
    nodes: list[CascadeNode]
    edges: list[CascadeEdge]
    narrative: list[str] = Field(
        default_factory=list, description="e.g. 'Flooded road -> longer ambulance route -> ...'"
    )
    assumptions: list[str] = Field(default_factory=list)
