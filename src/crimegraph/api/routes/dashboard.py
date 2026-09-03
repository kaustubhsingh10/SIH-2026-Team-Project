"""Investigation Command Dashboard API routes for CrimeGraph AI (Day 31).

Provides endpoints for unified operational command dashboard queries.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and RBAC policies.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.graph.dashboard import InvestigationDashboardService
from crimegraph.models.dashboard import DashboardResponse

router = APIRouter(prefix="", tags=["Command Dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/api/investigation/dashboard", response_model=DashboardResponse)
def get_investigation_dashboard(
    request: Request,
    case_id: Optional[str] = Query(None, description="Optional case ID filter (e.g. CASE_101)"),
    limit: int = Query(5, ge=1, le=50, description="Maximum items per section"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> DashboardResponse:
    """Retrieves unified operational command dashboard intelligence."""
    graph = request.app.state.graph
    service = InvestigationDashboardService(graph)

    try:
        res = service.get_dashboard(case_id=case_id, limit=limit)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit_logger.log(
        action="DASHBOARD_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "case_id": case_id,
            "limit": limit
        }
    )

    return res


@router.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_alias(
    request: Request,
    case_id: Optional[str] = Query(None, description="Optional case ID filter"),
    limit: int = Query(5, ge=1, le=50, description="Maximum items per section"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> DashboardResponse:
    """Alias endpoint for /api/investigation/dashboard."""
    return get_investigation_dashboard(request, case_id=case_id, limit=limit, current_user=current_user, audit_logger=audit_logger)
