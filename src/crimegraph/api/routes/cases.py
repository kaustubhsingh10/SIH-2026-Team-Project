"""Case API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from crimegraph.models.entities import EntityType
from crimegraph.graph.traversal import find_cross_case_connections
from crimegraph.graph.intelligence import NetworkIntelligenceEngine
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from pydantic import BaseModel, Field
from crimegraph.data.loader import save_manual_data

router = APIRouter(prefix="/api/cases", tags=["Cases"], dependencies=[Depends(get_current_user)])


class CaseCreateRequest(BaseModel):
    id: Optional[str] = Field(None, description="Optional unique Case ID (e.g. CASE_401). If omitted, an ID will be automatically generated.")
    title: str = Field(..., description="Short case title", min_length=1)
    case_number: Optional[str] = Field(None, description="Official case number or FIR number")
    description: Optional[str] = Field(None, description="Detailed case overview")
    case_type: Optional[str] = Field(None, description="Type of crime or case (e.g. HOMICIDE, CYBER_FRAUD, NARCOTICS, BURGLARY)")
    status: str = Field(default="ACTIVE", description="Case status (e.g. OPEN, ACTIVE, UNDER_INVESTIGATION, CLOSED)")
    priority: Optional[str] = Field(default="HIGH", description="Investigation priority (LOW, MEDIUM, HIGH, CRITICAL)")
    incident_date: Optional[str] = Field(None, description="Date/time of the incident (ISO 8601)")
    location_id: Optional[str] = Field(None, description="Primary incident location ID")
    locations: Optional[List[str]] = Field(default_factory=list, description="Associated location IDs or names")
    notes: Optional[str] = Field(None, description="Investigator context notes")
    source_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of source documents or initial evidence")


def _generate_unique_case_id(graph) -> str:
    """Generates a sequential or non-colliding unique CASE ID in CASE_XXX format."""
    import re
    existing_nums = []
    for eid in graph.entities:
        m = re.match(r"^CASE_(\d+)$", eid.upper())
        if m:
            existing_nums.append(int(m.group(1)))
    
    next_num = max(existing_nums, default=100) + 1
    cand_id = f"CASE_{next_num}"
    while cand_id in graph.entities:
        next_num += 1
        cand_id = f"CASE_{next_num}"
    return cand_id


@router.post("", status_code=201, response_model=Dict[str, Any])
def create_case(
    request: Request,
    payload: CaseCreateRequest,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Manually create a new investigation case, store it in the knowledge graph, and atomically persist it."""
    graph = request.app.state.graph
    
    # 1. Determine or validate Case ID
    case_id = payload.id.strip().upper() if payload.id and payload.id.strip() else _generate_unique_case_id(graph)
    if case_id in graph.entities:
        audit_logger.log(
            action="CASE_CREATE_FAILED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.CASE,
            resource_id=case_id,
            status=AuditStatus.FAILURE,
            details={"reason": f"Case ID '{case_id}' already exists."}
        )
        raise HTTPException(status_code=409, detail=f"Case with ID '{case_id}' already exists in knowledge graph.")

    case_number = payload.case_number or f"FIR-2026-MANUAL-{case_id.replace('CASE_', '')}"
    
    # 2. Build Case Entity
    case_dict = {
        "id": case_id,
        "entity_type": EntityType.CASE.value,
        "case_number": case_number,
        "title": payload.title.strip(),
        "description": payload.description or f"Manual investigation case: {payload.title.strip()}",
        "status": payload.status.upper(),
        "incident_date": payload.incident_date,
        "location_id": payload.location_id,
        "source_ids": payload.source_ids or [f"DOC_{case_id}_INITIAL_ENTRY.pdf"],
        "origin": "MANUAL",
        "case_type": payload.case_type,
        "priority": payload.priority,
        "notes": payload.notes,
        "created_by": current_user.username,
        "created_at": payload.incident_date
    }
    
    from crimegraph.models.entities import Case
    try:
        case_entity = Case(**case_dict)
    except Exception as e:
        audit_logger.log(
            action="CASE_CREATE_FAILED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.CASE,
            resource_id=case_id,
            status=AuditStatus.FAILURE,
            details={"error": str(e)}
        )
        raise HTTPException(status_code=422, detail=f"Validation error creating Case: {str(e)}")

    # 3. Add to graph store and persist atomically
    graph.add_entity(case_entity)
    save_manual_data(graph)

    audit_logger.log(
        action="CASE_CREATE",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        resource_id=case_id,
        case_id=case_id,
        status=AuditStatus.SUCCESS,
        details={
            "title": payload.title,
            "case_number": case_number,
            "status": payload.status,
            "priority": payload.priority,
            "created_by": current_user.username,
            "persisted": True
        }
    )

    resp = case_entity.model_dump()
    resp["persisted"] = True
    resp["created_by"] = current_user.username
    return resp


@router.get("", response_model=List[Dict[str, Any]])
def list_cases(
    request: Request,
    status: Optional[str] = Query(None, description="Filter cases by status (e.g. ACTIVE, CLOSED, UNDER_INVESTIGATION)"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Optional limit for pagination"),
    offset: int = Query(0, ge=0, description="Optional offset for pagination")
) -> List[Dict[str, Any]]:
    """List all cases registered in the knowledge graph."""
    graph = request.app.state.graph
    cases = graph.get_entities_by_type(EntityType.CASE)
    
    if status:
        cases = [c for c in cases if getattr(c, "status", "").lower() == status.lower()]

    if offset > 0:
        cases = cases[offset:]
    if limit is not None:
        cases = cases[:limit]
        
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
    case_a = case_a.strip()
    case_b = case_b.strip()
    
    if case_a not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_a}' not found in knowledge graph")
    if case_b not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_b}' not found in knowledge graph")
        
    connections = find_cross_case_connections(graph, case_a, case_b, max_depth=max_depth)
    return {"connections": connections}


@router.get("/{case_id}")
def get_case_details(
    request: Request,
    case_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieve detailed information about a specific case."""
    graph = request.app.state.graph
    case_id = case_id.strip()
    entity = graph.get_entity(case_id)
    
    if not entity or entity.entity_type != EntityType.CASE.value:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")
        
    audit_logger.log(
        action="CASE_VIEW",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        resource_id=case_id,
        case_id=case_id,
        status=AuditStatus.SUCCESS
    )
    return entity.model_dump()


@router.get("/{case_id}/graph")
def get_case_graph(request: Request, case_id: str) -> Dict[str, Any]:
    """Returns the visual graph data (nodes and edges) for a case.
    
    Strictly conforms to API_CONTRACT.md Section 3.
    """
    graph = request.app.state.graph
    case_id = case_id.strip()
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
    case_id = case_id.strip()
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")
        
    subgraph = graph.get_case_subgraph(case_id)
    nodes = subgraph.get("nodes", [])
    
    if entity_type:
        nodes = [n for n in nodes if n.get("entity_type", "").upper() == entity_type.strip().upper()]
        
    return nodes


@router.get("/{case_id}/influencers")
def get_case_influencers(
    request: Request,
    case_id: str,
    entity_type: Optional[str] = Query("PERSON", description="Filter by entity type (e.g. PERSON, PHONE, VEHICLE, or ALL)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of ranked entities to return"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieve deterministically ranked influencer entities and key individuals for a specific case.
    
    Supports SIH Problem Statement B3 — Key Individual and Influential Node Identification.
    """
    graph = request.app.state.graph
    case_id = case_id.strip()
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")

    filter_type = None if (not entity_type or entity_type.upper() in ["ALL", "*"]) else entity_type.strip().upper()
    engine = NetworkIntelligenceEngine(graph)

    try:
        data = engine.get_case_influencers(case_id=case_id, entity_type=filter_type, limit=limit)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit_logger.log(
        action="NETWORK_INTELLIGENCE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        resource_id=case_id,
        case_id=case_id,
        status=AuditStatus.SUCCESS,
        details={"filter_type": filter_type, "limit": limit, "results_count": data.get("results_count", 0)}
    )

    return data


@router.get("/{case_id}/network-intelligence")
def get_case_network_intelligence(
    request: Request,
    case_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieve comprehensive network topology intelligence, bridge detection, and cross-case linkages for a case."""
    graph = request.app.state.graph
    case_id = case_id.strip()
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found")

    engine = NetworkIntelligenceEngine(graph)
    try:
        data = engine.get_case_network_intelligence(case_id=case_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit_logger.log(
        action="NETWORK_INTELLIGENCE_OVERVIEW",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        resource_id=case_id,
        case_id=case_id,
        status=AuditStatus.SUCCESS
    )

    return data

