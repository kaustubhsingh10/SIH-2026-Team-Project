"""Authentication and Authorization Models for CrimeGraph AI."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """User roles for CrimeGraph role-based access control (RBAC)."""
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class User(BaseModel):
    """User account model."""
    model_config = ConfigDict(use_enum_values=True)

    username: str = Field(..., description="Unique username / identifier")
    hashed_password: str = Field(..., description="Securely hashed password (PBKDF2-SHA256)")
    full_name: Optional[str] = Field(default=None, description="Full name or badge number")
    role: UserRole = Field(default=UserRole.ANALYST, description="User role: ANALYST or ADMIN")
    is_active: bool = Field(default=True, description="Account active status")


class UserResponse(BaseModel):
    """Public user profile response (never exposes password hash)."""
    model_config = ConfigDict(use_enum_values=True)

    username: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool


class UserCreate(BaseModel):
    """Request model for creating a new user account (Admin only)."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.ANALYST)


class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Plaintext password")


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    """Internal token payload model."""
    sub: str
    role: UserRole
    exp: int
    iat: int
    jti: Optional[str] = None
