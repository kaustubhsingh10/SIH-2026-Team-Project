"""Security, password hashing, and cryptographic token utilities for CrimeGraph AI.

Uses Python standard library hashlib, hmac, and secrets.
Guarantees zero compiled binary dependencies and Python 3.11-3.14 compatibility.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from crimegraph.auth.models import TokenPayload, UserRole


# Secret key configuration
def get_secret_key() -> str:
    """Returns JWT secret key from environment or creates a deterministic runtime fallback."""
    return os.environ.get("CRIMEGRAPH_JWT_SECRET") or os.environ.get("JWT_SECRET_KEY") or "crimegraph-production-secret-key-2026-sih"


def get_token_expire_minutes() -> int:
    """Returns access token expiration in minutes (default: 60 minutes / 1 hour)."""
    try:
        return int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except ValueError:
        return 60


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte salt."""
    if not salt:
        salt = secrets.token_hex(16)
    
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    hash_hex = key.hex()
    return f"pbkdf2_sha256$100000${salt}${hash_hex}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2-SHA256 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        
        iterations = int(parts[1])
        salt = parts[2]
        expected_hash = parts[3]
        
        computed_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        return hmac.compare_digest(computed_key.hex(), expected_hash)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url string without trailing padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    """Decodes base64url string with padding restoration."""
    rem = len(s) % 4
    if rem > 0:
        s += "=" * (4 - rem)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(
    username: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None,
    custom_claims: Optional[Dict[str, Any]] = None
) -> Tuple[str, int]:
    """Generates an RFC 7519 compliant JWT access token signed with HMAC-SHA256.
    
    Returns (token_string, expires_in_seconds).
    """
    secret = get_secret_key()
    now = int(time.time())
    
    if expires_delta:
        expire_seconds = int(expires_delta.total_seconds())
    else:
        expire_seconds = get_token_expire_minutes() * 60
        
    exp = now + expire_seconds

    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    payload = {
        "sub": username,
        "role": role.value if hasattr(role, "value") else str(role),
        "iat": now,
        "exp": exp,
        "jti": secrets.token_hex(8)
    }

    if custom_claims:
        payload.update(custom_claims)

    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    header_b64 = _b64url_encode(header_json)
    payload_b64 = _b64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    return token, expire_seconds


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token signature and expiration timestamp.
    
    Raises ValueError on expired or invalid token.
    """
    secret = get_secret_key()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token: JWT must contain exactly 3 segments separated by dots")

    header_b64, payload_b64, signature_b64 = parts

    # 1. Verify Signature
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise ValueError("Invalid token signature")

    # 2. Parse Payload
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid token payload encoding: {str(e)}")

    # 3. Check Expiration
    exp = payload.get("exp")
    if not exp or not isinstance(exp, (int, float)):
        raise ValueError("Token missing 'exp' claim")

    now = int(time.time())
    if now >= exp:
        raise ValueError("Token has expired")

    return payload
