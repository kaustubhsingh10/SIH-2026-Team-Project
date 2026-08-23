"""Graph traversal and path discovery algorithms for CrimeGraph AI.

Implements cross-case connection discovery and path extraction with evidence aggregation.
Strictly adheres to API_CONTRACT.md Section 6.
"""

from typing import Any, Dict, List, Optional, Set
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import EntityType


def find_paths_between_entities(
    graph: KnowledgeGraphStore,
    source_id: str,
    target_id: str,
    max_depth: int = 6,
    directed: bool = False
) -> List[Dict[str, Any]]:
    """Discovers all simple paths connecting source_id and target_id within max_depth hops.
    
    Returns structured paths with edge details, supporting evidence, and aggregate confidence.
    """
    if source_id not in graph.entities:
        raise KeyError(f"Source entity '{source_id}' not found in graph")
    if target_id not in graph.entities:
        raise KeyError(f"Target entity '{target_id}' not found in graph")

    results: List[Dict[str, Any]] = []

    # BFS / DFS Queue: (current_node_id, [visited_node_ids], [traversed_rel_ids])
    queue: List[tuple] = [(source_id, [source_id], [])]

    while queue:
        current_node, visited_nodes, traversed_rels = queue.pop(0)

        if current_node == target_id and len(visited_nodes) > 1:
            # Reconstruct path metadata
            path_evidence_ids: Set[str] = set()
            edge_confidences: List[float] = []
            steps: List[Dict[str, Any]] = []

            for i, rel_id in enumerate(traversed_rels):
                rel = graph.get_relationship(rel_id)
                if not rel:
                    continue
                edge_confidences.append(rel.confidence)
                path_evidence_ids.update(rel.evidence_ids)

                u = visited_nodes[i]
                v = visited_nodes[i + 1]
                steps.append({
                    "from": u,
                    "to": v,
                    "relationship": rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship),
                    "relationship_id": rel.id,
                    "confidence": rel.confidence,
                    "evidence_ids": rel.evidence_ids
                })

            # Calculate composite confidence (minimum confidence along the evidence chain)
            composite_confidence = min(edge_confidences) if edge_confidences else 1.0

            # Find shared / pivot entities in the path (excluding source and target endpoints)
            intermediate_nodes = visited_nodes[1:-1]
            shared_entities = [
                nid for nid in intermediate_nodes
                if graph.entities[nid].entity_type in [
                    EntityType.PHONE.value,
                    EntityType.VEHICLE.value,
                    EntityType.LOCATION.value,
                    EntityType.ACCOUNT.value,
                    EntityType.PERSON.value,
                    EntityType.ORGANIZATION.value
                ]
            ]

            results.append({
                "source_id": source_id,
                "target_id": target_id,
                "path": visited_nodes,
                "shared_entities": shared_entities,
                "confidence": round(composite_confidence, 2),
                "evidence_ids": sorted(list(path_evidence_ids)),
                "steps": steps,
                "hop_count": len(traversed_rels)
            })
            continue

        if len(visited_nodes) - 1 >= max_depth:
            continue

        # Get adjacent edges
        direction = "outgoing" if directed else "undirected"
        for rel, neighbor in graph.get_neighbors(current_node, direction=direction):
            if neighbor.id not in visited_nodes:
                queue.append((
                    neighbor.id,
                    visited_nodes + [neighbor.id],
                    traversed_rels + [rel.id]
                ))

    # Sort results by shortest path first, then highest confidence
    results.sort(key=lambda x: (x["hop_count"], -x["confidence"]))
    return results


def find_cross_case_connections(
    graph: KnowledgeGraphStore,
    case_a: str,
    case_b: str,
    max_depth: int = 6
) -> List[Dict[str, Any]]:
    """Discovers relationship paths connecting two cases.
    
    Output strictly conforms to API_CONTRACT.md Section 6:
    {
      "connections": [
        {
          "case_a": "CASE_101",
          "case_b": "CASE_204",
          "shared_entities": ["PHONE_042"],
          "path": ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"],
          "confidence": 0.91,
          "evidence_ids": ["EVID_021", "EVID_034"]
        }
      ]
    }
    """
    raw_paths = find_paths_between_entities(graph, case_a, case_b, max_depth=max_depth, directed=False)
    
    connections = []
    for p in raw_paths:
        # Determine the key bridge entity (e.g. Phone, Vehicle, or Account)
        bridge_entities = [
            nid for nid in p["shared_entities"]
            if graph.entities[nid].entity_type in [
                EntityType.PHONE.value,
                EntityType.VEHICLE.value,
                EntityType.ACCOUNT.value,
                EntityType.LOCATION.value
            ]
        ]
        shared = bridge_entities if bridge_entities else p["shared_entities"]

        connections.append({
            "case_a": case_a,
            "case_b": case_b,
            "shared_entities": shared,
            "path": p["path"],
            "confidence": p["confidence"],
            "evidence_ids": p["evidence_ids"]
        })

    return connections
