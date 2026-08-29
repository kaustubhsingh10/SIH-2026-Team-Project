"""Audit Trail & Activity Logging API routes for CrimeGraph AI.

Tracks security, access control, and mutation events across the CrimeGraph platform.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])

# In-memory audit event log store
AUDIT_LOGS: List[Dict[str, Any]] = []


class AuditEvent(BaseModel):
    id: str
    timestamp: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    case_id: Optional[str] = None
    status: str  # "SUCCESS", "FAILURE", "DENIED"
    details: Optional[Dict[str, Any]] = None


def log_audit_event(
    actor: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str,
    case_id: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper function to record a structured activity event into the audit trail."""
    event = {
        "id": f"AUDIT_{uuid.uuid4().hex[:8].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor or "OFFICER_VERMA",
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id or "SYSTEM",
        "case_id": case_id,
        "status": status.upper(),
        "details": details or {}
    }
    # Prepend to maintain newest-first order
    AUDIT_LOGS.insert(0, event)
    return event


# Seed initial realistic demonstration audit events
if not AUDIT_LOGS:
    log_audit_event(
        actor="SYSTEM_INIT",
        action="SYSTEM_STARTUP",
        resource_type="KNOWLEDGE_GRAPH",
        resource_id="GRAPH_STORE",
        case_id="ALL",
        status="SUCCESS",
        details={"message": "Knowledge graph initialized with 34 nodes and 24 edges."}
    )
    log_audit_event(
        actor="OFFICER_VERMA",
        action="USER_LOGIN",
        resource_type="SESSION",
        resource_id="OFFICER_VERMA",
        case_id=None,
        status="SUCCESS",
        details={"agency_id": "AGY-SIH-2026", "role": "INVESTIGATOR"}
    )
    log_audit_event(
        actor="OFFICER_VERMA",
        action="GRAPH_RETRIEVAL",
        resource_type="CASE",
        resource_id="CASE_101",
        case_id="CASE_101",
        status="SUCCESS",
        details={"view": "Vis.js Graph Workspace"}
    )


@router.get("", response_model=List[Dict[str, Any]])
def list_audit_logs(
    case_id: Optional[str] = Query(None, description="Filter audit logs by case ID"),
    actor: Optional[str] = Query(None, description="Filter audit logs by actor username"),
    status: Optional[str] = Query(None, description="Filter audit logs by status (SUCCESS, FAILURE, DENIED)"),
    action: Optional[str] = Query(None, description="Filter audit logs by action type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of audit records to return")
) -> List[Dict[str, Any]]:
    """Retrieve dynamic audit logs from the CrimeGraph backend."""
    logs = AUDIT_LOGS

    if case_id:
        logs = [l for l in logs if l.get("case_id") == case_id or l.get("case_id") == "ALL"]
    if actor:
        logs = [l for l in logs if l.get("actor", "").lower() == actor.lower()]
    if status:
        logs = [l for l in logs if l.get("status", "").upper() == status.upper()]
    if action:
        logs = [l for l in logs if l.get("action", "").lower() == action.lower()]

    return logs[:limit]
