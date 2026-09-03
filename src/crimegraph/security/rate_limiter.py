"""Production-Safe In-Memory Sliding Window Rate Limiter for CrimeGraph AI.

Provides configurable, tier-based API abuse protection without external infrastructure.
Supports:
- Distinct rate limit tiers for AI investigations, mutations, and read endpoints.
- Client identification via JWT username (when authenticated) or sanitized client IP.
- Retry-After header calculation and sliding timestamp window pruning.
- Safe bypass for health checks and when RATE_LIMIT_ENABLED=false.
"""

import collections
import logging
import os
import threading
import time
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from crimegraph.auth.security import decode_access_token

logger = logging.getLogger("crimegraph.security.rate_limiter")


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        # client_key -> route_tier -> list of timestamps
        self._clients: Dict[str, Dict[str, collections.deque]] = collections.defaultdict(
            lambda: collections.defaultdict(collections.deque)
        )
        self._last_cleanup = time.time()

    def is_enabled(self) -> bool:
        """Checks if rate limiting is enabled via environment variable."""
        val = os.environ.get("RATE_LIMIT_ENABLED", "false").lower()
        return val in ("true", "1", "yes", "on")

    def get_tier_config(self, method: str, path: str) -> Tuple[str, int, int]:
        """Determines rate limit tier (name, max_requests, window_seconds) for request."""
        # 1. Health checks and interactive docs are exempt
        if path in ("/api/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"):
            return ("EXEMPT", 100000, 60)

        # 2. AI Investigator tier (computationally expensive)
        if path.startswith("/api/investigate"):
            max_req = int(os.environ.get("RATE_LIMIT_AI_REQUESTS", "20"))
            window = int(os.environ.get("RATE_LIMIT_AI_WINDOW_SECONDS", "60"))
            return ("AI", max_req, window)

        # 3. Mutation tier (state changes, auth, creation)
        if method in ("POST", "PUT", "DELETE", "PATCH") or path.startswith("/api/auth"):
            max_req = int(os.environ.get("RATE_LIMIT_MUTATION_REQUESTS", "30"))
            window = int(os.environ.get("RATE_LIMIT_MUTATION_WINDOW_SECONDS", "60"))
            return ("MUTATION", max_req, window)

        # 4. Standard read tier
        max_req = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
        window = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
        return ("DEFAULT", max_req, window)

    def extract_client_key(self, request: Request) -> str:
        """Extracts a reliable client key based on authenticated user or client IP."""
        # 1. Check authenticated JWT
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            try:
                payload = decode_access_token(token)
                username = payload.get("sub")
                if username:
                    return f"user:{username}"
            except Exception:
                pass

        # 2. Fallback to client IP with X-Forwarded-For reverse proxy support
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            return f"ip:{ip}"

        if request.client and request.client.host:
            return f"ip:{request.client.host}"

        return "client:anonymous"

    def check_rate_limit(self, request: Request) -> Tuple[bool, int, str]:
        """Evaluates whether the incoming request exceeds rate limits.
        
        Returns:
            (allowed: bool, retry_after_seconds: int, tier_name: str)
        """
        if not self.is_enabled():
            return (True, 0, "DISABLED")

        tier_name, max_requests, window_seconds = self.get_tier_config(request.method, request.url.path)
        if tier_name == "EXEMPT":
            return (True, 0, "EXEMPT")

        client_key = self.extract_client_key(request)
        now = time.time()

        with self._lock:
            # Periodic background cleanup of stale clients
            if now - self._last_cleanup > 300:
                self._cleanup_stale_entries(now)
                self._last_cleanup = now

            timestamps = self._clients[client_key][tier_name]

            # Evict timestamps older than the sliding window
            cutoff = now - window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            # Check if limit exceeded
            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest)))
                return (False, retry_after, tier_name)

            # Record current request
            timestamps.append(now)
            return (True, 0, tier_name)

    def _cleanup_stale_entries(self, now: float):
        """Prunes inactive client buckets to preserve memory."""
        stale_clients = []
        for client, tiers in self._clients.items():
            stale_tiers = []
            for tier, timestamps in tiers.items():
                while timestamps and timestamps[0] <= (now - 300):
                    timestamps.popleft()
                if not timestamps:
                    stale_tiers.append(tier)
            for t in stale_tiers:
                del tiers[t]
            if not tiers:
                stale_clients.append(client)
        for c in stale_clients:
            del self._clients[c]


rate_limiter = SlidingWindowRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing sliding-window rate limiting on all API routes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        allowed, retry_after, tier = rate_limiter.check_rate_limit(request)

        if not allowed:
            client_key = rate_limiter.extract_client_key(request)
            req_id = getattr(request.state, "request_id", "-")
            
            logger.warning(
                f"RATE_LIMIT_EXCEEDED [{tier}] on {request.method} {request.url.path} "
                f"from {client_key} (Retry-After: {retry_after}s) [req:{req_id}]"
            )

            # Log to audit trail if app audit_logger is initialized
            if hasattr(request.app.state, "audit_logger") and request.app.state.audit_logger:
                try:
                    from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
                    request.app.state.audit_logger.log(
                        action="RATE_LIMIT_EXCEEDED",
                        actor_id=client_key,
                        actor_type=AuditActorType.USER if client_key.startswith("user:") else AuditActorType.SYSTEM,
                        resource_type=AuditResourceType.SYSTEM,
                        status=AuditStatus.FAILURE,
                        details={
                            "path": str(request.url.path),
                            "method": request.method,
                            "tier": tier,
                            "retry_after": retry_after
                        }
                    )
                except Exception as log_err:
                    logger.debug(f"Audit log failed for rate limit event: {log_err}")

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please wait a moment and try again.",
                    "retry_after": retry_after,
                    "tier": tier
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Tier": tier,
                    "X-Request-ID": req_id if req_id != "-" else ""
                }
            )

        return await call_next(request)
