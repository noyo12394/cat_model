"""Living Cascade (section 14): infrastructure-dependency propagation.

Built on NetworkX rather than a bespoke graph structure, per the
architecture in section 34. Propagation is a simple breadth-first walk
outward from directly hazard-exposed nodes along dependency edges - explicit
and inspectable, matching the "no LLM for numeric outcomes" rule (section 26)
even though this is the Living Cascade visualization rather than the
Counterfactual Action Lab per se; the same engine backs both.
"""

from __future__ import annotations

from collections import deque

import networkx as nx

from app.db.memory_repository import MemoryRepository
from app.schemas.cascade import CascadeEdge, CascadeNode, CascadeResult
from app.schemas.enums import OperationalState

MINUTES_PER_HOP = 25.0


def build_graph(repo: MemoryRepository) -> nx.DiGraph:
    graph = nx.DiGraph()
    for facility in repo.list_facilities():
        graph.add_node(
            facility.facility_id,
            name=facility.name,
            facility_type=facility.facility_type.value,
            operational_state=facility.operational_state.value,
            served_population=facility.served_population or 0,
        )
    for dep in repo.list_dependencies():
        graph.add_edge(
            dep.from_facility_id,
            dep.to_facility_id,
            relationship=dep.relationship,
            strength=dep.strength,
            is_uncertain=dep.is_uncertain,
        )
    return graph


def run_cascade(
    repo: MemoryRepository,
    hazard_facility_ids: list[str],
    removed_facility_ids: list[str] | None = None,
    added_redundancy_edges: list[tuple[str, str]] | None = None,
) -> CascadeResult:
    graph = build_graph(repo)
    removed = set(removed_facility_ids or [])
    for node_id in removed:
        if graph.has_node(node_id):
            graph.remove_node(node_id)
    for a, b in added_redundancy_edges or []:
        if graph.has_node(a) and graph.has_node(b):
            graph.add_edge(a, b, relationship="provides_access_to", strength=0.6, is_uncertain=True)

    hops: dict[str, int] = {}
    queue: deque[str] = deque()
    for hazard_id in hazard_facility_ids:
        if graph.has_node(hazard_id) and hazard_id not in removed:
            hops[hazard_id] = 0
            queue.append(hazard_id)

    while queue:
        current = queue.popleft()
        for neighbor in graph.successors(current):
            if neighbor not in hops:
                hops[neighbor] = hops[current] + 1
                queue.append(neighbor)
        # Cascades also propagate to anything that DEPENDS ON a degraded node,
        # i.e. walk predecessors when the edge means "depends_on" reversed.
        for neighbor in graph.predecessors(current):
            edge = graph.edges[neighbor, current]
            if edge.get("relationship") in ("depends_on", "provides_access_to") and neighbor not in hops:
                hops[neighbor] = hops[current] + 1
                queue.append(neighbor)

    nodes: list[CascadeNode] = []
    for node_id, data in graph.nodes(data=True):
        hop = hops.get(node_id)
        nodes.append(
            CascadeNode(
                facility_id=node_id,
                name=data.get("name", node_id),
                facility_type=data.get("facility_type", "unknown"),
                operational_state=(
                    OperationalState.DEGRADED.value if hop == 0 else data.get("operational_state", "unknown")
                ),
                served_population=data.get("served_population", 0),
                directly_exposed=hop == 0,
                hops_from_hazard=hop,
                estimated_minutes_to_consequence=(hop * MINUTES_PER_HOP if hop is not None else None),
            )
        )
    for removed_id in removed:
        if not any(n.facility_id == removed_id for n in nodes):
            nodes.append(
                CascadeNode(
                    facility_id=removed_id,
                    name=removed_id,
                    facility_type="unknown",
                    operational_state=OperationalState.DOWN.value,
                    is_removed=True,
                )
            )

    edges = [
        CascadeEdge(
            from_facility_id=u,
            to_facility_id=v,
            relationship=data.get("relationship", "connected_to"),
            strength=data.get("strength", 0.5),
            is_uncertain=data.get("is_uncertain", False),
        )
        for u, v, data in graph.edges(data=True)
    ]

    narrative: list[str] = []
    ordered = sorted((n for n in nodes if n.hops_from_hazard is not None), key=lambda n: n.hops_from_hazard)
    for n in ordered:
        if n.hops_from_hazard == 0:
            narrative.append(f"{n.name} is directly exposed to the hazard.")
        else:
            narrative.append(
                f"-> {n.name} may be affected roughly {n.estimated_minutes_to_consequence:.0f} "
                f"minutes later ({n.hops_from_hazard} step(s) away)."
            )

    return CascadeResult(
        nodes=nodes,
        edges=edges,
        narrative=narrative,
        assumptions=[
            f"Propagation delay is approximated at {MINUTES_PER_HOP:.0f} minutes per dependency hop.",
            "Dependency strengths and directions come from the seeded infrastructure graph, not a live SCADA feed.",
        ],
    )
