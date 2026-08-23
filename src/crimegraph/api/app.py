"""CrimeGraph AI — Main FastAPI Application Entrypoint.

Provides the complete REST API server for Shruti's Frontend and Aditya's AI Intelligence Layer.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and PROJECT_SPEC.md.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.api.routes import cases, entities, graph, evidence, extract, reports, resolution, investigate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to initialize the knowledge graph store on startup."""
    # Initialize and load knowledge graph from data/synthetic_data.json
    app.state.graph = load_dataset()
    yield
    # Cleanup if needed on shutdown


def create_app(graph_instance: KnowledgeGraphStore = None) -> FastAPI:
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
        lifespan=lifespan if graph_instance is None else None
    )

    # If an explicit graph instance is provided, use it, otherwise load dataset
    if graph_instance is not None:
        app.state.graph = graph_instance
    else:
        app.state.graph = load_dataset()

    # Configure CORS for frontend clients (Stitch, React/Vite, Next.js, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health & root status endpoints
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
    def health_check() -> Dict[str, str]:
        return {"status": "healthy"}

    # Include modular routers
    app.include_router(cases.router)
    app.include_router(entities.router)
    app.include_router(graph.router)
    app.include_router(evidence.router)
    app.include_router(extract.router)
    app.include_router(reports.router)
    app.include_router(resolution.router)
    app.include_router(investigate.router)

    return app


# Default app instance for ASGI servers (e.g. uvicorn crimegraph.api.app:app)
app = create_app()
