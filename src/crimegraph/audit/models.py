"""Audit Trail and Activity Logging Models for CrimeGraph AI.

Strictly structured for forensic accountability, system auditing, and RBAC visibility.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AuditActorType(str, Enum):
    """Originator type for audit events."""
    USER = "USER"
    SYSTEM = "SYSTEM"
    AI = "AI"


class AuditResourceType(str, Enum):
    """Target resource category."""
    AUTH = "AUTH"
    ENTITY = "ENTITY"
    RELATIONSHIP = "RELATIONSHIP"
    CASE = "CASE"
    INVESTIGATION = "INVESTIGATION"
    EVIDENCE = "EVIDENCE"
    SOURCE = "SOURCE"
    SYSTEM = "SYSTEM"


class AuditStatus(str, Enum):
    """Outcome status of the recorded action."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class AuditEvent(BaseModel):
    """Structured audit event record."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    event_id: str = Field(default_factory=lambda: f"AUDIT_{uuid.uuid4().hex[:12].upper()}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor_id: str = Field(default="SYSTEM", description="Username or system component identifier")
    actor_type: AuditActorType = Field(default=AuditActorType.USER)
    action: str = Field(..., description="Action name (e.g. AUTH_LOGIN_SUCCESS, ENTITY_CREATE)")
    resource_type: AuditResourceType = Field(default=AuditResourceType.SYSTEM)
    resource_id: Optional[str] = Field(default=None, description="Identifier of the target entity/case/etc.")
    case_id: Optional[str] = Field(default=None, description="Linked case ID if relevant")
    status: AuditStatus = Field(default=AuditStatus.SUCCESS)
    details: Dict[str, Any] = Field(default_factory=dict, description="Non-sensitive contextual metadata")


class AuditLogResponse(BaseModel):
    """Paginated/filtered response model for GET /api/audit."""
    total_count: int
    filtered_count: int
    events: List[AuditEvent]
