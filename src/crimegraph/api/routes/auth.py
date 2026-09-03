"""Authentication API routes for CrimeGraph AI.

Provides login, token issuance, profile retrieval, and user management endpoints.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request, status

from crimegraph.auth.models import LoginRequest, Token, User, UserCreate, UserResponse, UserRole
from crimegraph.auth.security import create_access_token, verify_password
from crimegraph.auth.dependencies import get_current_user, get_user_store, require_admin
from crimegraph.auth.store import UserStore
from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    user_store: UserStore = Depends(get_user_store),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Token:
    """Authenticates user credentials and returns a signed JWT access token."""
    username = payload.username.lower().strip()
    user = user_store.get_user(username)

    if not user or not verify_password(payload.password, user.hashed_password):
        audit_logger.log(
            action="AUTH_LOGIN_FAILED",
            actor_id=username or "ANONYMOUS",
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.AUTH,
            status=AuditStatus.FAILURE,
            details={"reason": "Invalid credentials provided"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        audit_logger.log(
            action="AUTH_LOGIN_DENIED",
            actor_id=user.username,
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.AUTH,
            status=AuditStatus.DENIED,
            details={"reason": "Account is deactivated"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    user_role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    token_str, expire_seconds = create_access_token(
        username=user.username,
        role=user_role
    )

    audit_logger.log(
        action="AUTH_LOGIN_SUCCESS",
        actor_id=user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.AUTH,
        status=AuditStatus.SUCCESS,
        details={"role": user_role.value if hasattr(user_role, "value") else str(user_role)}
    )

    return Token(
        access_token=token_str,
        token_type="bearer",
        expires_in=expire_seconds,
        user=UserResponse(
            username=user.username,
            full_name=user.full_name,
            role=user_role,
            is_active=user.is_active
        )
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Returns the authenticated user's profile and role permissions."""
    user_role = current_user.role if isinstance(current_user.role, UserRole) else UserRole(current_user.role)
    return UserResponse(
        username=current_user.username,
        full_name=current_user.full_name,
        role=user_role,
        is_active=current_user.is_active
    )


@router.get("/users", response_model=List[UserResponse])
def list_users(
    admin_user: User = Depends(require_admin),
    user_store: UserStore = Depends(get_user_store)
) -> List[UserResponse]:
    """Lists all registered CrimeGraph user accounts (Admin role required)."""
    users = user_store.list_users()
    return [
        UserResponse(
            username=u.username,
            full_name=u.full_name,
            role=u.role if isinstance(u.role, UserRole) else UserRole(u.role),
            is_active=u.is_active
        ) for u in users
    ]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    admin_user: User = Depends(require_admin),
    user_store: UserStore = Depends(get_user_store),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> UserResponse:
    """Creates a new user account (Admin role required)."""
    try:
        new_user = user_store.create_user(payload)
        user_role = new_user.role if isinstance(new_user.role, UserRole) else UserRole(new_user.role)
        audit_logger.log(
            action="USER_CREATE",
            actor_id=admin_user.username,
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.AUTH,
            resource_id=new_user.username,
            status=AuditStatus.SUCCESS,
            details={"created_user": new_user.username, "role": user_role.value if hasattr(user_role, "value") else str(user_role)}
        )
        return UserResponse(
            username=new_user.username,
            full_name=new_user.full_name,
            role=user_role,
            is_active=new_user.is_active
        )
    except ValueError as e:
        audit_logger.log(
            action="USER_CREATE_FAILED",
            actor_id=admin_user.username,
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.AUTH,
            resource_id=payload.username,
            status=AuditStatus.FAILURE,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
