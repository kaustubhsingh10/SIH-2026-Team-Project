"""Authentication & Authorization API routes for CrimeGraph AI.

Provides authentication endpoints (login, me, logout) and server-side authorization enforcement.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Header, Request, status

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory active tokens store
ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}


class LoginRequest(BaseModel):
    username: str = Field(..., description="Investigator ID / Username")
    password: str = Field(..., description="Authorization Key / Password")
    agency_id: Optional[str] = Field(None, description="Optional Agency ID")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


def verify_bearer_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Dependency helper to verify Bearer authentication token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = parts[1]
    if token not in ACTIVE_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ACTIVE_TOKENS[token]


def verify_case_access(user: Dict[str, Any], case_id: Optional[str]) -> None:
    """Enforces server-side case-level access authorization boundaries."""
    if not case_id or case_id == "ALL":
        return
    allowed = user.get("allowed_cases", [])
    if allowed and "ALL" not in allowed and case_id not in allowed:
        from crimegraph.api.routes.audit import log_audit_event
        log_audit_event(
            actor=user.get("username"),
            action="CASE_ACCESS_DENIED",
            resource_type="CASE",
            resource_id=case_id,
            case_id=case_id,
            status="DENIED",
            details={"allowed_cases": allowed}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User '{user.get('username')}' is not authorized to access case '{case_id}'."
        )


def verify_write_permission(user: Dict[str, Any]) -> None:
    """Enforces server-side write authorization rules."""
    if user.get("role") == "READ_ONLY":
        from crimegraph.api.routes.audit import log_audit_event
        log_audit_event(
            actor=user.get("username"),
            action="WRITE_PERMISSION_DENIED",
            resource_type="MUTATION",
            resource_id="ENTITY_MUTATION",
            case_id=None,
            status="DENIED",
            details={"role": user.get("role")}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: User '{user.get('username')}' lacks write authorization to perform entity or relationship mutations."
        )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate an investigator and return a Bearer access token."""
    uname = payload.username.strip()
    pwd = payload.password.strip()

    if not uname or not pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password cannot be empty."
        )

    # Determine user role & case access authorization rules
    role = "INVESTIGATOR"
    allowed_cases = ["CASE_101", "CASE_204", "CASE_102", "CASE_305", "ALL"]

    uname_upper = uname.upper()
    if "RESTRICTED" in uname_upper:
        role = "RESTRICTED_INVESTIGATOR"
        allowed_cases = ["CASE_101", "CASE_102"]
    elif "READONLY" in uname_upper or "ANALYST" in uname_upper:
        role = "READ_ONLY"
        allowed_cases = ["CASE_101", "CASE_102", "CASE_204", "CASE_305", "ALL"]

    import uuid
    token = f"cg_token_{uuid.uuid4().hex[:16]}"
    user_info = {
        "username": uname,
        "agency_id": (payload.agency_id or "AGY-SIH-2026").strip(),
        "role": role,
        "allowed_cases": allowed_cases,
        "authenticated_at": "2026-08-29T09:50:00Z"
    }
    ACTIVE_TOKENS[token] = user_info

    from crimegraph.api.routes.audit import log_audit_event
    log_audit_event(
        actor=uname,
        action="USER_LOGIN",
        resource_type="SESSION",
        resource_id=uname,
        case_id=None,
        status="SUCCESS",
        details={"agency_id": user_info["agency_id"], "role": role}
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=user_info
    )


@router.get("/me")
def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Retrieve details for the currently authenticated user."""
    user = verify_bearer_token(authorization)
    return {"status": "authenticated", "user": user}


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Revoke active session token."""
    user = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            user = ACTIVE_TOKENS.pop(parts[1], None)

    from crimegraph.api.routes.audit import log_audit_event
    log_audit_event(
        actor=user.get("username") if user else "OFFICER",
        action="USER_LOGOUT",
        resource_type="SESSION",
        resource_id=user.get("username") if user else "SESSION",
        case_id=None,
        status="SUCCESS"
    )

    return {"status": "logged_out", "message": "Session terminated successfully."}
