"""CrimeGraph AI — Main FastAPI Application Entrypoint.

Provides the complete REST API server for Shruti's Frontend and Aditya's AI Intelligence Layer.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and PROJECT_SPEC.md.
"""

from contextlib import asynccontextmanager
import logging
import os
from typing import Any, Dict
from fastapi import FastAPI, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest

from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.auth.store import UserStore
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.observability.logging import setup_observability_logging
from crimegraph.observability.middleware import ObservabilityMiddleware
from crimegraph.observability.metrics import metrics
from crimegraph.security.rate_limiter import RateLimitMiddleware
from crimegraph.api.routes import (
    audit,
    auth,
    cases,
    communities,
    entities,
    graph,
    evidence,
    extract,
    reports,
    resolution,
    entity_resolution_legacy,
    investigate,
    relationships,
    patterns,
    sources,
    timeline,
    intelligence,
    paths,
    dashboard,
    correlation,
    risk,
)

# Initialize production structured logging
logger = setup_observability_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to initialize knowledge graph, users, and audit stores on startup."""
    logger.info("Initializing CrimeGraph AI application services...")
    if getattr(app.state, "graph", None) is None:
        app.state.graph = load_dataset()
    if getattr(app.state, "user_store", None) is None:
        app.state.user_store = UserStore()
    if getattr(app.state, "audit_logger", None) is None:
        app.state.audit_logger = AuditLogger()
        app.state.audit_logger.log(
            action="SYSTEM_STARTUP",
            actor_id="SYSTEM",
            actor_type=AuditActorType.SYSTEM,
            resource_type=AuditResourceType.SYSTEM,
            status=AuditStatus.SUCCESS,
            details={"version": "1.0.0"}
        )
    logger.info(
        f"CrimeGraph AI initialization complete. "
        f"Graph entities: {len(app.state.graph.entities)}, "
        f"Relationships: {len(app.state.graph.relationships)}, "
        f"Evidence items: {len(app.state.graph.evidence)}. Server ready."
    )
    yield
    logger.info("CrimeGraph AI backend shutting down cleanly.")


def create_app(
    graph_instance: KnowledgeGraphStore = None,
    user_store: UserStore = None,
    audit_logger: AuditLogger = None
) -> FastAPI:
    """Factory to create and configure the FastAPI application."""
    app = FastAPI(
        title="CrimeGraph AI — Investigative Intelligence API",
        description=(
            "REST backend for CrimeGraph AI (SIH 2026). "
            "Converts fragmented investigation records into an evidence-linked knowledge graph."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan if graph_instance is None and user_store is None and audit_logger is None else None
    )

    # Observability & Request Performance Middleware
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # If an explicit graph instance is provided, use it, otherwise load dataset
    if graph_instance is not None:
        app.state.graph = graph_instance
    else:
        app.state.graph = load_dataset()

    # User store initialization
    if user_store is not None:
        app.state.user_store = user_store
    else:
        app.state.user_store = UserStore()

    # Audit logger initialization
    if audit_logger is not None:
        app.state.audit_logger = audit_logger
    else:
        app.state.audit_logger = AuditLogger()
        app.state.audit_logger.log(
            action="SYSTEM_STARTUP",
            actor_id="SYSTEM",
            actor_type=AuditActorType.SYSTEM,
            resource_type=AuditResourceType.SYSTEM,
            status=AuditStatus.SUCCESS,
            details={"version": "1.0.0"}
        )

    # Configure CORS for frontend clients (Stitch, React/Vite, Next.js, Netlify, etc.)
    cors_env = os.environ.get("CORS_ORIGINS") or os.environ.get("CRIMEGRAPH_FRONTEND_ORIGIN") or "*"
    allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
    if not allowed_origins:
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler to prevent raw traceback or local path leakage
    @app.exception_handler(Exception)
    async def global_exception_handler(request: StarletteRequest, exc: Exception):
        req_id = getattr(request.state, "request_id", "-")
        logger.error(f"Unhandled error processing {request.method} {request.url.path} [req:{req_id}]: {exc}", exc_info=True)
        if hasattr(request.app.state, "audit_logger") and request.app.state.audit_logger:
            request.app.state.audit_logger.log(
                action="SYSTEM_ERROR",
                actor_id="SYSTEM",
                actor_type=AuditActorType.SYSTEM,
                resource_type=AuditResourceType.SYSTEM,
                status=AuditStatus.FAILURE,
                details={"path": str(request.url.path), "method": request.method, "error": str(exc)}
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please contact the administrator."},
            headers={"X-Request-ID": req_id} if req_id != "-" else {}
        )

    # Health & root status endpoints (conforms strictly to API_CONTRACT.md)
    @app.get("/", tags=["System"])
    def root_status() -> Dict[str, Any]:
        graph_store = getattr(app.state, "graph", None)
        return {
            "system": "CrimeGraph AI",
            "name": "CrimeGraph AI Backend API",
            "version": "1.0.0",
            "status": "operational",
            "disclaimer": "CrimeGraph AI provides investigative leads only. Not a proof of guilt. All leads require human verification.",
            "documentation": "/docs",
            "metrics": {
                "entity_count": len(graph_store.entities) if graph_store else 0,
                "relationship_count": len(graph_store.relationships) if graph_store else 0,
                "evidence_count": len(graph_store.evidence) if graph_store else 0
            }
        }

    @app.get("/api/health", tags=["System"])
    def health_check(metrics_flag: bool = Query(False, alias="metrics", description="Include performance metrics")) -> Dict[str, Any]:
        graph_store = getattr(app.state, "graph", None)
        if graph_store is None or len(graph_store.entities) == 0:
            return {"status": "degraded", "detail": "Knowledge graph store uninitialized"}
        
        resp = {"status": "healthy"}
        if metrics_flag:
            resp["diagnostics"] = metrics.get_summary()
        return resp

    @app.get("/api/metrics", tags=["System"])
    def get_metrics() -> Dict[str, Any]:
        """Provides in-memory performance and observability summary."""
        return metrics.get_summary()

    # Include modular routers
    app.include_router(audit.router)
    app.include_router(auth.router)
    app.include_router(cases.router)
    app.include_router(communities.router)
    app.include_router(entities.router)
    app.include_router(graph.router)
    app.include_router(evidence.router)
    app.include_router(extract.router)
    app.include_router(reports.router)
    app.include_router(resolution.router)
    app.include_router(entity_resolution_legacy.router)
    app.include_router(investigate.router)
    app.include_router(relationships.router)
    app.include_router(patterns.router)
    app.include_router(sources.router)
    app.include_router(timeline.router)
    app.include_router(intelligence.router)
    app.include_router(paths.router)
    app.include_router(dashboard.router)
    app.include_router(correlation.router)
    app.include_router(risk.router)

    # Static files mount for UI (serves web directory at /web)
    app_file = os.path.abspath(__file__)
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(app_file))))
    web_dir = os.path.join(proj_root, "web")
    if os.path.exists(web_dir):
        from fastapi.staticfiles import StaticFiles
        app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")

    return app


# Default app instance for ASGI servers (e.g. uvicorn crimegraph.api.app:app)
app = create_app()
