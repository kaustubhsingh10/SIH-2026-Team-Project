"""Entity API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
Supports manual entity creation, updating, and safe deletion.
"""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from crimegraph.models.entities import EntityType
from crimegraph.graph.store import ENTITY_TYPE_MAP
from crimegraph.data.loader import save_manual_data
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus

router = APIRouter(prefix="/api/entities", tags=["Entities"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[Dict[str, Any]])
def list_entities(
    request: Request,
    type: Optional[str] = Query(None, description="Entity type filter (e.g. PERSON, PHONE, VEHICLE, LOCATION, ACCOUNT, ORGANIZATION, EVENT, CASE)"),
    search: Optional[str] = Query(None, description="Search query string against names, numbers, or identifiers"),
    case_id: Optional[str] = Query(None, description="Filter entities linked to a specific case"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score threshold"),
    origin: Optional[str] = Query(None, description="Filter by data origin: DATASET or MANUAL"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of entities to return (optional pagination)"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> List[Dict[str, Any]]:
    """Search and filter entities across the entire knowledge graph."""
    graph = request.app.state.graph
    
    # 1. Base set of entities
    if type:
        upper_type = type.upper()
        entities = graph.get_entities_by_type(upper_type)
    else:
        entities = graph.get_all_entities()
        
    # 2. Filter by origin
    if origin:
        upper_orig = origin.upper()
        entities = [e for e in entities if getattr(e, "origin", "DATASET") == upper_orig]

    # 3. Filter by case_id if specified
    if case_id:
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        subgraph = graph.get_case_subgraph(case_id)
        case_entity_ids = {node["id"] for node in subgraph.get("nodes", [])}
        entities = [e for e in entities if e.id in case_entity_ids]
        
    # 4. Filter by search text
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
        
    # 5. Filter by minimum confidence
    if min_confidence is not None:
        entities = [e for e in entities if getattr(e, "confidence", 1.0) >= min_confidence]

    # 6. Apply pagination if requested
    if offset > 0:
        entities = entities[offset:]
    if limit is not None:
        entities = entities[:limit]
        
    return [e.model_dump() for e in entities]


@router.post("", status_code=201, response_model=Dict[str, Any])
def create_entity(
    request: Request,
    payload: Dict[str, Any],
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new manual entity and persist to storage."""
    graph = request.app.state.graph
    raw_type = (payload.get("entity_type") or payload.get("type") or "").strip().upper()
    if not raw_type or raw_type not in ENTITY_TYPE_MAP:
        audit_logger.log(
            action="ENTITY_CREATE_FAILED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.ENTITY,
            status=AuditStatus.FAILURE,
            details={"reason": f"Invalid entity_type: '{raw_type}'"}
        )
        raise HTTPException(
            status_code=422,
            detail=f"Invalid or missing entity_type: '{raw_type}'. Supported types: {list(ENTITY_TYPE_MAP.keys())}"
        )

    # Generate unique ID if not supplied
    entity_id = payload.get("id")
    if not entity_id or not str(entity_id).strip():
        unique_suffix = hex(int(time.time() * 1000))[2:][-6:].upper()
        entity_id = f"MANUAL_{raw_type}_{unique_suffix}"
    else:
        entity_id = str(entity_id).strip()
        if entity_id in graph.entities:
            audit_logger.log(
                action="ENTITY_CREATE_FAILED",
                actor_id=current_user.username,
                resource_type=AuditResourceType.ENTITY,
                resource_id=entity_id,
                status=AuditStatus.FAILURE,
                details={"reason": "Entity ID already exists"}
            )
            raise HTTPException(status_code=409, detail=f"Entity with ID '{entity_id}' already exists.")

    payload["id"] = entity_id
    payload["entity_type"] = raw_type
    payload["origin"] = "MANUAL"

    model_cls = ENTITY_TYPE_MAP[raw_type]
    try:
        validated_entity = model_cls(**payload)
    except Exception as e:
        audit_logger.log(
            action="ENTITY_CREATE_FAILED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.ENTITY,
            resource_id=entity_id,
            status=AuditStatus.FAILURE,
            details={"error": str(e)}
        )
        raise HTTPException(status_code=422, detail=f"Validation error for {raw_type}: {str(e)}")

    graph.add_entity(validated_entity)
    save_manual_data(graph)

    audit_logger.log(
        action="ENTITY_CREATE",
        actor_id=current_user.username,
        resource_type=AuditResourceType.ENTITY,
        resource_id=validated_entity.id,
        status=AuditStatus.SUCCESS,
        details={
            "entity_type": raw_type,
            "name": getattr(validated_entity, "name", getattr(validated_entity, "title", raw_type))
        }
    )
    return validated_entity.model_dump()


@router.get("/{entity_id}")
def get_entity(
    request: Request,
    entity_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieve full entity details, connected relationships, cases, and supporting evidence.
    
    Strictly conforms to API_CONTRACT.md Section 5:
    GET /api/entities/{entity_id}
    """
    graph = request.app.state.graph
    entity_id = entity_id.strip()
    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity with ID '{entity_id}' not found")
        
    try:
        details = graph.get_entity_details(entity_id)
        audit_logger.log(
            action="ENTITY_VIEW",
            actor_id=current_user.username,
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.ENTITY,
            resource_id=entity_id,
            status=AuditStatus.SUCCESS
        )
        return details
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{entity_id}", response_model=Dict[str, Any])
def update_entity(
    request: Request,
    entity_id: str,
    payload: Dict[str, Any],
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a manual entity's properties."""
    graph = request.app.state.graph
    entity_id = entity_id.strip()
    existing = graph.get_entity(entity_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    existing_dict = existing.model_dump()
    for k, v in payload.items():
        if k not in ("id", "entity_type"):
            existing_dict[k] = v

    raw_type = existing.entity_type
    model_cls = ENTITY_TYPE_MAP[raw_type]
    try:
        updated_entity = model_cls(**existing_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")

    graph.add_entity(updated_entity)
    save_manual_data(graph)

    audit_logger.log(
        action="ENTITY_UPDATE",
        actor_id=current_user.username,
        resource_type=AuditResourceType.ENTITY,
        resource_id=entity_id,
        status=AuditStatus.SUCCESS,
        details={"entity_type": raw_type}
    )
    return updated_entity.model_dump()


@router.delete("/{entity_id}")
def delete_entity(
    request: Request,
    entity_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a manually created entity and connected edges."""
    graph = request.app.state.graph
    entity_id = entity_id.strip()
    existing = graph.get_entity(entity_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    if getattr(existing, "origin", "DATASET") == "DATASET":
        audit_logger.log(
            action="ENTITY_DELETE_DENIED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.ENTITY,
            resource_id=entity_id,
            status=AuditStatus.DENIED,
            details={"reason": "Protected dataset entity cannot be deleted"}
        )
        raise HTTPException(
            status_code=403,
            detail="Protected dataset entity cannot be deleted. Only manually created entities can be deleted."
        )

    graph.remove_entity(entity_id)
    save_manual_data(graph)

    audit_logger.log(
        action="ENTITY_DELETE",
        actor_id=current_user.username,
        resource_type=AuditResourceType.ENTITY,
        resource_id=entity_id,
        status=AuditStatus.SUCCESS
    )
    return {"status": "deleted", "id": entity_id, "message": f"Entity '{entity_id}' deleted successfully."}


@router.get("/{entity_id}/neighbors")
def get_entity_neighbors(
    request: Request,
    entity_id: str,
    direction: str = Query("undirected", pattern="^(undirected|outgoing|incoming)$", description="Adjacency direction")
) -> Dict[str, Any]:
    """Retrieve immediate 1-hop connected neighbors and relationships for an entity."""
    graph = request.app.state.graph
    entity_id = entity_id.strip()
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
