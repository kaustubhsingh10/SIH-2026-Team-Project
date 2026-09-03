"""Relationship API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
Supports manual relationship creation and safe deletion.
"""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from crimegraph.models.relationships import Relationship, RelationshipType
from crimegraph.data.loader import save_manual_data
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus

router = APIRouter(prefix="/api/relationships", tags=["Relationships"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[Dict[str, Any]])
def list_relationships(
    request: Request,
    type: Optional[str] = Query(None, description="Filter by relationship type"),
    source_id: Optional[str] = Query(None, description="Filter by source entity ID"),
    target_id: Optional[str] = Query(None, description="Filter by target entity ID"),
    origin: Optional[str] = Query(None, description="Filter by data origin: DATASET or MANUAL"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit returned relationships")
) -> List[Dict[str, Any]]:
    """List and filter relationships across the knowledge graph."""
    graph = request.app.state.graph
    rels = graph.get_all_relationships()

    if type:
        upper_t = type.upper()
        rels = [r for r in rels if (r.relationship.value if hasattr(r.relationship, "value") else str(r.relationship)).upper() == upper_t]

    if source_id:
        rels = [r for r in rels if r.source_id == source_id.strip()]

    if target_id:
        rels = [r for r in rels if r.target_id == target_id.strip()]

    if origin:
        upper_orig = origin.upper()
        rels = [r for r in rels if getattr(r, "origin", "DATASET") == upper_orig]

    if limit:
        rels = rels[:limit]

    return [r.model_dump() for r in rels]


@router.post("", status_code=201, response_model=Dict[str, Any])
def create_relationship(
    request: Request,
    payload: Dict[str, Any],
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new manual relationship between two existing entities."""
    graph = request.app.state.graph

    source_id = str(payload.get("source_id") or "").strip()
    target_id = str(payload.get("target_id") or "").strip()
    rel_type_raw = str(payload.get("relationship") or payload.get("relationship_type") or "").strip().upper()

    if not source_id:
        raise HTTPException(status_code=422, detail="Missing required field 'source_id'")
    if not target_id:
        raise HTTPException(status_code=422, detail="Missing required field 'target_id'")
    if not rel_type_raw:
        raise HTTPException(status_code=422, detail="Missing required field 'relationship'")

    if source_id not in graph.entities:
        audit_logger.log(
            action="RELATIONSHIP_CREATE_FAILED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.RELATIONSHIP,
            status=AuditStatus.FAILURE,
            details={"reason": f"Source entity '{source_id}' does not exist"}
        )
        raise HTTPException(status_code=404, detail=f"Source entity '{source_id}' does not exist in graph.")
    if target_id not in graph.entities:
        audit_logger.log(
            action="RELATIONSHIP_CREATE_FAILED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.RELATIONSHIP,
            status=AuditStatus.FAILURE,
            details={"reason": f"Target entity '{target_id}' does not exist"}
        )
        raise HTTPException(status_code=404, detail=f"Target entity '{target_id}' does not exist in graph.")

    # Validate relationship type
    valid_rel_types = {rt.value for rt in RelationshipType}
    if rel_type_raw not in valid_rel_types:
        try:
            rel_type = RelationshipType(rel_type_raw)
        except ValueError:
            audit_logger.log(
                action="RELATIONSHIP_CREATE_FAILED",
                actor_id=current_user.username,
                resource_type=AuditResourceType.RELATIONSHIP,
                status=AuditStatus.FAILURE,
                details={"reason": f"Invalid relationship type '{rel_type_raw}'"}
            )
            raise HTTPException(
                status_code=422,
                detail=f"Invalid relationship type '{rel_type_raw}'. Allowed types: {sorted(list(valid_rel_types))}"
            )
    else:
        rel_type = RelationshipType(rel_type_raw)

    rel_id = payload.get("id")
    if not rel_id or not str(rel_id).strip():
        unique_suffix = hex(int(time.time() * 1000))[2:][-6:].upper()
        rel_id = f"REL_MANUAL_{unique_suffix}"
    else:
        rel_id = str(rel_id).strip()
        if rel_id in graph.relationships:
            raise HTTPException(status_code=409, detail=f"Relationship with ID '{rel_id}' already exists.")

    confidence = payload.get("confidence", 1.0)
    try:
        confidence = float(confidence)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Confidence must be a valid float between 0.0 and 1.0")

    if not (0.0 <= confidence <= 1.0):
        raise HTTPException(status_code=422, detail="Confidence must be between 0.0 and 1.0")

    rel_obj = Relationship(
        id=rel_id,
        source_id=source_id,
        relationship=rel_type,
        target_id=target_id,
        confidence=confidence,
        evidence_ids=payload.get("evidence_ids", []),
        properties=payload.get("properties", {}),
        origin="MANUAL"
    )

    graph.add_relationship(rel_obj)
    save_manual_data(graph)

    audit_logger.log(
        action="RELATIONSHIP_CREATE",
        actor_id=current_user.username,
        resource_type=AuditResourceType.RELATIONSHIP,
        resource_id=rel_obj.id,
        status=AuditStatus.SUCCESS,
        details={
            "source_id": source_id,
            "target_id": target_id,
            "relationship": rel_type.value if hasattr(rel_type, "value") else str(rel_type),
            "confidence": confidence
        }
    )
    return rel_obj.model_dump()


@router.delete("/{rel_id}")
def delete_relationship(
    request: Request,
    rel_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a manually created relationship edge."""
    graph = request.app.state.graph
    rel_id = rel_id.strip()
    existing = graph.get_relationship(rel_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Relationship '{rel_id}' not found")

    if getattr(existing, "origin", "DATASET") == "DATASET":
        audit_logger.log(
            action="RELATIONSHIP_DELETE_DENIED",
            actor_id=current_user.username,
            resource_type=AuditResourceType.RELATIONSHIP,
            resource_id=rel_id,
            status=AuditStatus.DENIED,
            details={"reason": "Protected dataset relationship cannot be deleted"}
        )
        raise HTTPException(
            status_code=403,
            detail="Protected dataset relationship cannot be deleted. Only manually created relationships can be deleted."
        )

    graph.remove_relationship(rel_id)
    save_manual_data(graph)

    audit_logger.log(
        action="RELATIONSHIP_DELETE",
        actor_id=current_user.username,
        resource_type=AuditResourceType.RELATIONSHIP,
        resource_id=rel_id,
        status=AuditStatus.SUCCESS
    )
    return {"status": "deleted", "id": rel_id, "message": f"Relationship '{rel_id}' deleted successfully."}
