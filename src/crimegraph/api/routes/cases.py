"""Case API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from crimegraph.models.entities import EntityType
from crimegraph.graph.traversal import find_cross_case_connections

router = APIRouter(prefix="/api/cases", tags=["Cases"])


@router.get("", response_model=List[Dict[str, Any]])
def list_cases(
    request: Request,
    status: Optional[str] = Query(None, description="Filter cases by status (e.g. ACTIVE, CLOSED, UNDER_INVESTIGATION)")
) -> List[Dict[str, Any]]:
    """List all cases registered in the knowledge graph."""
    graph = request.app.state.graph
    cases = graph.get_entities_by_type(EntityType.CASE)
    
    if status:
        cases = [c for c in cases if getattr(c, "status", "").lower() == status.lower()]
        
    return [c.model_dump() for c in cases]


@router.get("/connections")
def get_case_connections(
    request: Request,
    case_a: str = Query(..., description="First Case ID (e.g. CASE_101)"),
    case_b: str = Query(..., description="Second Case ID (e.g. CASE_204)"),
    max_depth: int = Query(6, ge=1, le=10, description="Maximum hops to search for paths")
) -> Dict[str, Any]:
    """Find discoverable multi-hop relationship connections between two cases.
    
    Strictly conforms to API_CONTRACT.md Section 6.
    """
    graph = request.app.state.graph
    
    if case_a not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_a}' not found in knowledge graph")
    if case_b not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_b}' not found in knowledge graph")
        
    connections = find_cross_case_connections(graph, case_a, case_b, max_depth=max_depth)
    return {"connections": connections}


@router.get("/{case_id}")
def get_case_details(request: Request, case_id: str) -> Dict[str, Any]:
    """Retrieve detailed information about a specific case."""
    graph = request.app.state.graph
    entity = graph.get_entity(case_id)
    
    if not entity or entity.entity_type != EntityType.CASE.value:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")
        
    return entity.model_dump()


@router.get("/{case_id}/graph")
def get_case_graph(request: Request, case_id: str) -> Dict[str, Any]:
    """Returns the visual graph data (nodes and edges) for a case.
    
    Strictly conforms to API_CONTRACT.md Section 3.
    """
    graph = request.app.state.graph
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")
        
    try:
        return graph.get_case_subgraph(case_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}/entities")
def get_case_entities(
    request: Request,
    case_id: str,
    entity_type: Optional[str] = Query(None, description="Optional entity type filter (e.g. PERSON, VEHICLE, PHONE)")
) -> List[Dict[str, Any]]:
    """Retrieve all entities directly or 1-hop connected to a specific case."""
    graph = request.app.state.graph
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")
        
    subgraph = graph.get_case_subgraph(case_id)
    nodes = subgraph.get("nodes", [])
    
    if entity_type:
        nodes = [n for n in nodes if n.get("entity_type", "").upper() == entity_type.upper()]
        
    return nodes


@router.get("/{case_id}/timeline")
def get_case_timeline(request: Request, case_id: str) -> Dict[str, Any]:
    """Returns chronological events related to this case.
    
    Strictly conforms to API_CONTRACT.md Section 7.
    """
    graph = request.app.state.graph
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")
        
    case_entity = graph.get_entity(case_id)
    subgraph = graph.get_case_subgraph(case_id)
    involved_entity_ids = {node["id"] for node in subgraph.get("nodes", [])}
    
    all_events = graph.get_entities_by_type(EntityType.EVENT)
    case_events = []
    
    for ev in all_events:
        # Check if event is directly in the case subgraph
        if ev.id in involved_entity_ids:
            case_events.append(ev)
            continue
            
        # Check if event involves a person in the case or matches case location
        ev_loc = getattr(ev, "location_id", None)
        case_loc = getattr(case_entity, "location_id", None)
        if ev_loc and case_loc and ev_loc == case_loc:
            case_events.append(ev)
            continue
            
        # Check neighbors of event
        for rel, neighbor in graph.get_neighbors(ev.id):
            if neighbor.id in involved_entity_ids:
                case_events.append(ev)
                break
                
    # Sort events chronologically by timestamp (ascending)
    def parse_timestamp(event):
        ts = getattr(event, "timestamp", None)
        return ts if ts else ""
        
    sorted_events = sorted(case_events, key=parse_timestamp)
    
    event_dicts = []
    for e in sorted_events:
        event_dicts.append({
            "id": e.id,
            "timestamp": getattr(e, "timestamp", None),
            "type": getattr(e, "event_type", "EVENT"),
            "location_id": getattr(e, "location_id", None),
            "description": getattr(e, "description", None)
        })
        
    return {"events": event_dicts}
