"""Entity API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from crimegraph.models.entities import EntityType

router = APIRouter(prefix="/api/entities", tags=["Entities"])


@router.get("", response_model=List[Dict[str, Any]])
def list_entities(
    request: Request,
    type: Optional[str] = Query(None, description="Entity type filter (e.g. PERSON, PHONE, VEHICLE, LOCATION, ACCOUNT, ORGANIZATION, EVENT, CASE)"),
    search: Optional[str] = Query(None, description="Search query string against names, numbers, or identifiers"),
    case_id: Optional[str] = Query(None, description="Filter entities linked to a specific case"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score threshold")
) -> List[Dict[str, Any]]:
    """Search and filter entities across the entire knowledge graph."""
    graph = request.app.state.graph
    
    # 1. Base set of entities
    if type:
        upper_type = type.upper()
        entities = graph.get_entities_by_type(upper_type)
    else:
        entities = graph.get_all_entities()
        
    # 2. Filter by case_id if specified
    if case_id:
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        subgraph = graph.get_case_subgraph(case_id)
        case_entity_ids = {node["id"] for node in subgraph.get("nodes", [])}
        entities = [e for e in entities if e.id in case_entity_ids]
        
    # 3. Filter by search text
    if search:
        search_lower = search.lower()
        filtered = []
        for e in entities:
            name = getattr(e, "name", "")
            title = getattr(e, "title", "")
            phone = getattr(e, "phone_number", "")
            reg = getattr(e, "registration_number", "")
            ident = getattr(e, "identifier", "")
            aliases = getattr(e, "aliases", [])
            
            match_found = (
                search_lower in e.id.lower() or
                search_lower in name.lower() or
                search_lower in title.lower() or
                search_lower in phone.lower() or
                search_lower in reg.lower() or
                search_lower in ident.lower() or
                any(search_lower in str(a).lower() for a in aliases)
            )
            if match_found:
                filtered.append(e)
        entities = filtered
        
    # 4. Filter by minimum confidence
    if min_confidence is not None:
        entities = [e for e in entities if getattr(e, "confidence", 1.0) >= min_confidence]
        
    return [e.model_dump() for e in entities]


@router.get("/{entity_id}")
def get_entity(request: Request, entity_id: str) -> Dict[str, Any]:
    """Retrieve full entity details, connected relationships, cases, and supporting evidence.
    
    Strictly conforms to API_CONTRACT.md Section 5:
    GET /api/entities/{entity_id}
    """
    graph = request.app.state.graph
    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity with ID '{entity_id}' not found")
        
    try:
        return graph.get_entity_details(entity_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{entity_id}/neighbors")
def get_entity_neighbors(
    request: Request,
    entity_id: str,
    direction: str = Query("undirected", pattern="^(undirected|outgoing|incoming)$", description="Adjacency direction")
) -> Dict[str, Any]:
    """Retrieve immediate 1-hop connected neighbors and relationships for an entity."""
    graph = request.app.state.graph
    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity with ID '{entity_id}' not found")
        
    neighbors_raw = graph.get_neighbors(entity_id, direction=direction)
    
    results = []
    for rel, neighbor in neighbors_raw:
        results.append({
            "relationship": rel.model_dump(),
            "neighbor": neighbor.model_dump()
        })
        
    return {
        "entity_id": entity_id,
        "neighbor_count": len(results),
        "neighbors": results
    }
