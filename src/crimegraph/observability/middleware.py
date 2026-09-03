"""Observability and Request Performance Middleware for CrimeGraph AI.

Monitors every API request, injects X-Request-ID correlation headers,
measures microsecond-level latency, updates metrics registry, and logs slow queries.
"""

import logging
import os
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from crimegraph.observability.metrics import metrics

logger = logging.getLogger("crimegraph.request")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for non-intrusive latency tracking and correlation ID injection."""

    def __init__(self, app, slow_threshold_ms: float = 500.0):
        super().__init__(app)
        self.slow_threshold_ms = float(os.environ.get("SLOW_REQUEST_THRESHOLD_MS", slow_threshold_ms))

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:10]}"
        request.state.request_id = req_id

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

            # Record in metrics collector
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            # Structured logging
            extra = {"request_id": req_id}
            log_line = f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)"
            
            if duration_ms >= self.slow_threshold_ms:
                logger.warning(f"SLOW REQUEST: {log_line} (Threshold: {self.slow_threshold_ms}ms)", extra=extra)
            elif response.status_code >= 400:
                logger.info(f"CLIENT/APP ERROR: {log_line}", extra=extra)
            else:
                logger.info(f"OK: {log_line}", extra=extra)

            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms
            )
            logger.error(f"UNHANDLED EXCEPTION on {request.method} {request.url.path} ({duration_ms}ms): {exc}", extra={"request_id": req_id})
            raise exc
