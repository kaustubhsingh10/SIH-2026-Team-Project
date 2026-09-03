"""FastAPI Authentication and Authorization Dependencies for CrimeGraph AI.

Provides role-based access control (RBAC) and JWT token extraction.
"""

import os
from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from crimegraph.auth.models import User, UserRole
from crimegraph.auth.security import decode_access_token
from crimegraph.auth.store import UserStore

# Optional HTTPBearer to integrate with Swagger UI / OpenAPI docs
security_scheme = HTTPBearer(auto_error=False)


def is_auth_strict() -> bool:
    """Checks whether strict token requirement is enforced.
    
    Defaults to True when CRIMEGRAPH_AUTH_STRICT or CRIMEGRAPH_AUTH_REQUIRED is set to true.
    """
    val = os.environ.get("CRIMEGRAPH_AUTH_STRICT") or os.environ.get("CRIMEGRAPH_AUTH_REQUIRED")
    if val is not None:
        return val.lower() in ("true", "1", "yes", "on")
    return False


def get_user_store(request: Request) -> UserStore:
    """Retrieves the global UserStore attached to app state or initializes one."""
    if hasattr(request.app.state, "user_store") and request.app.state.user_store is not None:
        return request.app.state.user_store
    
    store = UserStore()
    request.app.state.user_store = store
    return store


async def get_current_user(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    user_store: UserStore = Depends(get_user_store)
) -> User:
    """Dependency to extract, decode, and validate the current authenticated user from Bearer token."""
    token = None

    if auth_creds and auth_creds.credentials:
        token = auth_creds.credentials.strip()
    else:
        # Check raw Authorization header as fallback
        raw_header = request.headers.get("Authorization")
        if raw_header and raw_header.lower().startswith("bearer "):
            token = raw_header[7:].strip()

    # 1. If Token is provided: must be strictly valid
    if token:
        try:
            payload = decode_access_token(token)
            username = payload.get("sub")
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject claim",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            user = user_store.get_user(username)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account not found or disabled",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return user
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # 2. If No Token is provided:
    if is_auth_strict():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Default analyst context in non-strict test/development environment
    default_user = user_store.get_user("analyst")
    if default_user:
        return default_user

    return User(
        username="analyst",
        hashed_password="",
        full_name="Default Dev Analyst",
        role=UserRole.ANALYST,
        is_active=True
    )


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """Dependency factory that verifies the authenticated user has at least one of the allowed roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role if isinstance(current_user.role, UserRole) else UserRole(current_user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: Role '{user_role.value}' is not authorized for this operation. Required: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


# Role convenience shortcuts
require_analyst = require_role([UserRole.ANALYST, UserRole.ADMIN])
require_admin = require_role([UserRole.ADMIN])
