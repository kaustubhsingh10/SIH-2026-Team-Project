"""Advanced Link Analysis & Path Discovery API routes for CrimeGraph AI (Day 29).

Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and Safety Principles.
Exposes endpoints for advanced multi-hop path discovery and explainable link analysis.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from crimegraph.auth.dependencies import get_current_user
from crimegraph.graph.paths import AdvancedPathEngine
from crimegraph.models.paths import PathAnalysisRequest, PathAnalysisResponse

router = APIRouter(prefix="/api/paths", tags=["Path Discovery"], dependencies=[Depends(get_current_user)])


@router.post("/analyze", response_model=PathAnalysisResponse)
def analyze_paths_post(
    request: Request,
    payload: PathAnalysisRequest
) -> PathAnalysisResponse:
    """Execute advanced multi-hop link analysis and explainable path discovery (POST)."""
    graph = request.app.state.graph
    engine = AdvancedPathEngine(graph)

    try:
        return engine.analyze_paths(
            source_id=payload.source_id,
            target_id=payload.target_id,
            max_depth=payload.max_depth,
            limit=payload.limit,
            include_temporal=payload.include_temporal
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analyze", response_model=PathAnalysisResponse)
def analyze_paths_get(
    request: Request,
    source_id: str = Query(..., description="Source entity or case ID"),
    target_id: str = Query(..., description="Target entity or case ID"),
    max_depth: int = Query(5, ge=1, le=10, description="Maximum hop depth limit"),
    limit: int = Query(5, ge=1, le=50, description="Maximum candidate paths to return"),
    include_temporal: bool = Query(True, description="Evaluate chronological alignment")
) -> PathAnalysisResponse:
    """Execute advanced multi-hop link analysis and explainable path discovery (GET)."""
    graph = request.app.state.graph
    engine = AdvancedPathEngine(graph)

    try:
        return engine.analyze_paths(
            source_id=source_id,
            target_id=target_id,
            max_depth=max_depth,
            limit=limit,
            include_temporal=include_temporal
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/case-connections")
def analyze_case_connections(
    request: Request,
    case_a: str = Query(..., description="First case ID"),
    case_b: str = Query(..., description="Second case ID"),
    max_depth: int = Query(6, ge=1, le=10, description="Maximum hop depth")
) -> Dict[str, Any]:
    """Discover cross-case multi-hop connection paths between two investigation cases."""
    graph = request.app.state.graph
    engine = AdvancedPathEngine(graph)

    case_a = case_a.strip()
    case_b = case_b.strip()

    if case_a not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_a}' not found in knowledge graph store")
    if case_b not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_b}' not found in knowledge graph store")

    analysis_res = engine.analyze_paths(
        source_id=case_a,
        target_id=case_b,
        max_depth=max_depth,
        limit=10
    )

    connections = []
    for p in analysis_res.paths:
        connections.append({
            "case_a": case_a,
            "case_b": case_b,
            "shared_entities": p.shared_entities,
            "path": p.path,
            "path_score": p.path_score,
            "confidence": p.confidence,
            "evidence_ids": p.evidence_ids,
            "explanation": p.explanation
        })

    return {
        "case_a": case_a,
        "case_b": case_b,
        "total_connections": len(connections),
        "connections": connections,
        "safety_notice": analysis_res.safety_notice
    }
