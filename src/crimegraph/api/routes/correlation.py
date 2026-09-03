"""Cross-Source Intelligence Correlation API routes for CrimeGraph AI (Day 32).

Provides REST endpoints for querying multi-source intelligence correlations and contradictions.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and RBAC policies.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.graph.correlation import CrossSourceCorrelationEngine
from crimegraph.models.correlation import (
    CorrelationItem,
    CorrelationRequest,
    CorrelationQueryResponse,
    CorrelationType,
)

router = APIRouter(prefix="", tags=["Cross-Source Correlation"], dependencies=[Depends(get_current_user)])


@router.get("/api/correlations", response_model=CorrelationQueryResponse)
def get_correlations(
    request: Request,
    case_id: Optional[str] = Query(None, description="Optional case ID filter (e.g. CASE_101)"),
    entity_id: Optional[str] = Query(None, description="Optional entity ID filter (e.g. PERSON_017)"),
    correlation_type: Optional[str] = Query(None, description="Optional correlation type filter"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum correlation score threshold"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CorrelationQueryResponse:
    """Retrieves multi-source intelligence correlations matching query filters."""
    graph = request.app.state.graph
    engine = CrossSourceCorrelationEngine(graph)

    if isinstance(case_id, str) and case_id.strip():
        case_id = case_id.strip().upper()
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case ID '{case_id}' not found")
    else:
        case_id = None

    if isinstance(entity_id, str) and entity_id.strip():
        entity_id = entity_id.strip().upper()
        if entity_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Entity ID '{entity_id}' not found")
    else:
        entity_id = None

    raw_items = engine.detect_all_correlations(
        case_id=case_id,
        entity_id=entity_id,
        correlation_type=correlation_type,
        min_score=min_score,
        limit=limit
    )

    items = [CorrelationItem(**item) for item in raw_items]

    audit_logger.log(
        action="CORRELATION_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "case_id": case_id,
            "entity_id": entity_id,
            "correlation_type": correlation_type,
            "total_count": len(items)
        }
    )

    return CorrelationQueryResponse(correlations=items, total_count=len(items))


@router.get("/api/correlations/{correlation_id}", response_model=CorrelationItem)
def get_correlation_by_id(
    request: Request,
    correlation_id: str,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CorrelationItem:
    """Retrieves detailed information for a single detected correlation."""
    graph = request.app.state.graph
    engine = CrossSourceCorrelationEngine(graph)

    raw_items = engine.detect_all_correlations(limit=500)
    found = next((item for item in raw_items if item.get("correlation_id") == correlation_id), None)

    if not found:
        raise HTTPException(status_code=404, detail=f"Correlation ID '{correlation_id}' not found")

    audit_logger.log(
        action="CORRELATION_DETAIL_VIEW",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={"correlation_id": correlation_id}
    )

    return CorrelationItem(**found)


@router.post("/api/correlations/analyze", response_model=CorrelationQueryResponse)
def analyze_correlations(
    request: Request,
    req_body: CorrelationRequest,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CorrelationQueryResponse:
    """Executes a custom threshold cross-source correlation analysis sweep."""
    return get_correlations(
        request=request,
        case_id=req_body.case_id,
        entity_id=req_body.entity_id,
        correlation_type=req_body.correlation_type.value if req_body.correlation_type else None,
        min_score=req_body.min_score,
        limit=req_body.limit,
        current_user=current_user,
        audit_logger=audit_logger
    )


@router.get("/api/cases/{case_id}/correlations", response_model=CorrelationQueryResponse)
def get_case_correlations(
    request: Request,
    case_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CorrelationQueryResponse:
    """Retrieves cross-source correlations associated with a specific case."""
    return get_correlations(
        request=request,
        case_id=case_id,
        entity_id=None,
        correlation_type=None,
        min_score=0.0,
        limit=limit,
        current_user=current_user,
        audit_logger=audit_logger
    )


@router.get("/api/entities/{entity_id}/correlations", response_model=CorrelationQueryResponse)
def get_entity_correlations(
    request: Request,
    entity_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CorrelationQueryResponse:
    """Retrieves cross-source correlations associated with a specific entity."""
    return get_correlations(
        request=request,
        case_id=None,
        entity_id=entity_id,
        correlation_type=None,
        min_score=0.0,
        limit=limit,
        current_user=current_user,
        audit_logger=audit_logger
    )
