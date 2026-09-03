"""Audit Trail API routes for CrimeGraph AI.

Provides paginated, filtered access to the forensic audit log.
Strictly adheres to API contracts and RBAC rules.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request

from crimegraph.audit.models import AuditEvent, AuditLogResponse
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=AuditLogResponse)
def get_audit_log(
    request: Request,
    actor_id: Optional[str] = Query(None, description="Filter by actor identifier/username"),
    action: Optional[str] = Query(None, description="Filter by action name (e.g. AUTH_LOGIN_SUCCESS, ENTITY_CREATE)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (ENTITY, RELATIONSHIP, CASE, INVESTIGATION, AUTH)"),
    case_id: Optional[str] = Query(None, description="Filter events linked to a specific case ID"),
    status: Optional[str] = Query(None, description="Filter by status (SUCCESS, FAILURE, DENIED)"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    current_user: User = Depends(get_current_user)
) -> AuditLogResponse:
    """Retrieve filtered, append-oriented system and user audit trail records."""
    total_events = len(audit_logger.events)
    filtered_events = audit_logger.get_events(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        case_id=case_id,
        status=status,
        limit=limit,
        offset=offset
    )
    filtered_count = audit_logger.count_events(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        case_id=case_id,
        status=status
    )

    return AuditLogResponse(
        total_count=total_events,
        filtered_count=filtered_count,
        events=filtered_events
    )
