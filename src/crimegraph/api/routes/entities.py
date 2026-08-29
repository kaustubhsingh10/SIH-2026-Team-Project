"""Entity API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request
from crimegraph.models.entities import EntityType
from crimegraph.api.routes.auth import verify_bearer_token, verify_write_permission

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


@router.post("", status_code=201)
def create_entity(
    request: Request,
    data: Dict[str, Any],
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Manually create a new entity in the knowledge graph store."""
    if authorization:
        user = verify_bearer_token(authorization)
        verify_write_permission(user)

    graph = request.app.state.graph
    
    raw_type = (data.get("type") or data.get("entity_type") or "PERSON").upper()
    if raw_type == "SUSPECT":
        raw_type = "PERSON"
    data["type"] = raw_type
    data["entity_type"] = raw_type
    
    if not data.get("id"):
        prefix_map = {
            "PERSON": "PERSON",
            "PHONE": "PHONE",
            "VEHICLE": "VEHICLE",
            "LOCATION": "LOC",
            "ORGANIZATION": "ORG",
            "ACCOUNT": "ACC",
            "CASE": "CASE",
            "EVENT": "EVENT"
        }
        prefix = prefix_map.get(raw_type, "ENT")
        import random
        num = random.randint(100, 999)
        candidate_id = f"{prefix}_{num}"
        while candidate_id in graph.entities:
            num = random.randint(100, 999)
            candidate_id = f"{prefix}_{num}"
        data["id"] = candidate_id

    fallback_name = data.get("name") or data.get("title") or data.get("phone_number") or data.get("registration_number") or data.get("identifier") or data["id"]
    if raw_type in ["PERSON", "LOCATION", "ORGANIZATION", "EVENT"]:
        data["name"] = fallback_name
    elif raw_type == "PHONE":
        data["phone_number"] = data.get("phone_number") or fallback_name
    elif raw_type == "VEHICLE":
        data["registration_number"] = data.get("registration_number") or fallback_name
    elif raw_type == "ACCOUNT":
        data["account_type"] = data.get("account_type", "BANK_ACCOUNT")
        data["identifier"] = data.get("identifier") or fallback_name
    elif raw_type == "CASE":
        data["case_number"] = data.get("case_number") or data["id"]
        data["title"] = data.get("title") or fallback_name
        
    data["source"] = data.get("source", "Manual")
    data["is_manual"] = True
    
    try:
        created = graph.add_entity(data)
        try:
            from crimegraph.data.loader import save_dataset
            save_dataset(graph)
        except Exception:
            pass

        from crimegraph.api.routes.audit import log_audit_event
        actor_name = user.get("username") if 'user' in locals() and user else "OFFICER_VERMA"
        log_audit_event(
            actor=actor_name,
            action="CREATE_ENTITY",
            resource_type=data.get("type", "ENTITY"),
            resource_id=data.get("id"),
            case_id=data.get("case_id"),
            status="SUCCESS",
            details={"name": data.get("name"), "is_manual": True}
        )

        return created.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create entity: {str(e)}")


@router.put("/{entity_id}")
def update_entity(
    request: Request,
    entity_id: str,
    data: Dict[str, Any],
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Update properties of an existing entity in the knowledge graph store."""
    if authorization:
        user = verify_bearer_token(authorization)
        verify_write_permission(user)

    graph = request.app.state.graph
    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity with ID '{entity_id}' not found")
        
    existing = graph.entities[entity_id]
    existing_dict = existing.model_dump()
    
    for k, v in data.items():
        if k != "id" and v is not None:
            existing_dict[k] = v
            
    existing_dict["source"] = existing_dict.get("source", "Manual")
    existing_dict["is_manual"] = True
    
    try:
        updated = graph.add_entity(existing_dict)
        try:
            from crimegraph.data.loader import save_dataset
            save_dataset(graph)
        except Exception:
            pass
        return updated.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update entity: {str(e)}")


@router.delete("/{entity_id}")
def delete_entity(
    request: Request,
    entity_id: str,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Delete an entity and all its connected relationships from the graph store."""
    if authorization:
        user = verify_bearer_token(authorization)
        verify_write_permission(user)

    graph = request.app.state.graph
    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity with ID '{entity_id}' not found")
        
    # Remove entity
    del graph.entities[entity_id]
    
    # Remove from type index
    for t, eids in graph._type_index.items():
        eids.discard(entity_id)
        
    # Remove connected relationships
    rels_to_delete = [rid for rid, r in graph.relationships.items() if r.source_id == entity_id or r.target_id == entity_id]
    for rid in rels_to_delete:
        rel = graph.relationships.pop(rid, None)
        if rel:
            if rid in graph._outgoing.get(rel.source_id, []):
                graph._outgoing[rel.source_id].remove(rid)
            if rid in graph._incoming.get(rel.target_id, []):
                graph._incoming[rel.target_id].remove(rid)
            if rid in graph._undirected.get(rel.source_id, []):
                graph._undirected[rel.source_id].remove(rid)
            if rid in graph._undirected.get(rel.target_id, []):
                graph._undirected[rel.target_id].remove(rid)
                
    try:
        from crimegraph.data.loader import save_dataset
        save_dataset(graph)
    except Exception:
        pass

    return {"success": True, "deleted_id": entity_id}

