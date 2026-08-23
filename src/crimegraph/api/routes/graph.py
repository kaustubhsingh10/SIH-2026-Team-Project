"""Graph & Pathfinding API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from crimegraph.graph.traversal import find_paths_between_entities

router = APIRouter(prefix="", tags=["Graph"])


@router.get("/api/graph")
def get_graph(
    request: Request,
    entity_type: Optional[str] = Query(None, description="Filter nodes by entity type"),
    relationship_type: Optional[str] = Query(None, description="Filter edges by relationship type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter edges by minimum confidence"),
    case_id: Optional[str] = Query(None, description="Filter graph to a specific case subgraph")
) -> Dict[str, Any]:
    """Retrieve full knowledge graph or filtered graph view."""
    graph = request.app.state.graph
    
    if case_id:
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        return graph.get_case_subgraph(case_id)
        
    all_entities = graph.get_all_entities()
    all_relationships = graph.get_all_relationships()
    
    # Filter nodes
    if entity_type:
        all_entities = [e for e in all_entities if e.entity_type == entity_type.upper()]
    valid_node_ids = {e.id for e in all_entities}
    
    # Filter edges
    filtered_edges = []
    for r in all_relationships:
        if r.source_id not in valid_node_ids or r.target_id not in valid_node_ids:
            continue
        if relationship_type:
            rel_val = r.relationship.value if hasattr(r.relationship, "value") else str(r.relationship)
            if rel_val.upper() != relationship_type.upper():
                continue
        if min_confidence is not None:
            if r.confidence < min_confidence:
                continue
        filtered_edges.append(r)
        
    return {
        "nodes": [e.model_dump() for e in all_entities],
        "edges": [r.model_dump() for r in filtered_edges]
    }


@router.get("/api/paths")
def get_paths_between_entities(
    request: Request,
    source_id: str = Query(..., description="Starting entity ID (e.g. CASE_101, PERSON_017)"),
    target_id: str = Query(..., description="Target entity ID (e.g. CASE_204, VEHICLE_042)"),
    max_depth: int = Query(6, ge=1, le=10, description="Maximum traversal depth in hops"),
    directed: bool = Query(False, description="Whether to follow directional edges strictly")
) -> Dict[str, Any]:
    """Discover all connected relationship paths between any two entities in the graph."""
    graph = request.app.state.graph
    
    if source_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Source entity '{source_id}' not found in graph")
    if target_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Target entity '{target_id}' not found in graph")
        
    paths = find_paths_between_entities(
        graph=graph,
        source_id=source_id,
        target_id=target_id,
        max_depth=max_depth,
        directed=directed
    )
    
    return {
        "source_id": source_id,
        "target_id": target_id,
        "path_count": len(paths),
        "paths": paths
    }
