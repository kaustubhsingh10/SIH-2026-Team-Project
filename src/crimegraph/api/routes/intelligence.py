"""Intelligence & Key Player API routes for CrimeGraph AI (Day 28).

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
Provides explainable Key Player & Influencer Intelligence endpoints.
Includes /api/intelligence/key-players and /api/influence/* route aliases.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from crimegraph.auth.dependencies import get_current_user
from crimegraph.communities.engine import CommunityDetectionEngine
from crimegraph.graph.intelligence import NetworkIntelligenceEngine
from crimegraph.models.intelligence import KeyPlayerResponse

router = APIRouter(prefix="", tags=["Intelligence"], dependencies=[Depends(get_current_user)])


@router.get("/api/intelligence/key-players", response_model=KeyPlayerResponse)
@router.get("/api/influence", response_model=KeyPlayerResponse)
def get_key_players(
    request: Request,
    case_id: Optional[str] = Query(None, description="Filter key players to a specific case scope"),
    role: Optional[str] = Query(None, description="Filter by Key Player role (e.g. CORE_HUB, BRIDGE_ENTITY, CROSS_CASE_INFLUENCER)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. PERSON, PHONE, VEHICLE, or ALL)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of ranked key players to return"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite influence score filter")
) -> KeyPlayerResponse:
    """Retrieve explainable Key Player & Influencer Intelligence across knowledge graph or case scope."""
    graph = request.app.state.graph
    engine = NetworkIntelligenceEngine(graph)

    try:
        return engine.get_advanced_key_players(
            case_id=case_id,
            role=role,
            entity_type=entity_type,
            limit=limit,
            min_score=min_score
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/intelligence/key-players/{case_id}", response_model=KeyPlayerResponse)
def get_case_key_players(
    request: Request,
    case_id: str,
    role: Optional[str] = Query(None, description="Filter by Key Player role"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of key players to return"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score filter")
) -> KeyPlayerResponse:
    """Retrieve explainable Key Player & Influencer Intelligence for a specific case."""
    graph = request.app.state.graph
    engine = NetworkIntelligenceEngine(graph)

    case_id = case_id.strip()
    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in knowledge graph store")

    try:
        return engine.get_advanced_key_players(
            case_id=case_id,
            role=role,
            entity_type=entity_type,
            limit=limit,
            min_score=min_score
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/influence/rankings")
def get_influence_rankings(
    request: Request,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(10, ge=1, le=100, description="Limit output count")
) -> Dict[str, Any]:
    """Alias for network influence rankings."""
    graph = request.app.state.graph
    engine = NetworkIntelligenceEngine(graph)
    filter_type = None if (not entity_type or entity_type.upper() in ["ALL", "*"]) else entity_type.strip().upper()
    results = engine.rank_entities(entity_type=filter_type, limit=limit)
    return {
        "entity_type_filter": entity_type.upper() if entity_type else "ALL",
        "total_entities_analyzed": len(graph.entities),
        "results_count": len(results),
        "rankings": results
    }


@router.get("/api/influence/entity/{entity_id}")
def get_entity_influence(request: Request, entity_id: str) -> Dict[str, Any]:
    """Retrieve detailed influence metrics and Key Player classification for a single entity."""
    graph = request.app.state.graph
    entity_id = entity_id.strip()

    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in knowledge graph store")

    engine = NetworkIntelligenceEngine(graph)
    res = engine.get_advanced_key_players(limit=100)

    for kp in res.key_players:
        if kp.entity_id == entity_id:
            return {
                "entity_id": entity_id,
                "key_player_details": kp.model_dump(),
                "safety_notice": res.safety_notice
            }

    # If entity exists in store but is outside top 100
    metrics = engine.calculate_entity_metrics(entity_id)
    reasons = engine.generate_explanation_reasons(metrics)
    explanation = engine.generate_explanation_text(metrics)

    return {
        "entity_id": entity_id,
        "key_player_details": {
            "entity_id": entity_id,
            "entity_name": metrics["entity_name"],
            "entity_type": metrics["entity_type"],
            "score": metrics["influence_score"],
            "influence_role": metrics["influence_role"].value if hasattr(metrics["influence_role"], "value") else str(metrics["influence_role"]),
            "metrics": metrics["metrics"],
            "connected_case_ids": metrics["connected_cases"],
            "supporting_evidence_ids": metrics["supporting_evidence_ids"],
            "provenance": metrics["provenance"],
            "explanation": explanation,
            "reasons": reasons,
            "confidence": metrics["confidence"]
        },
        "safety_notice": res.safety_notice
    }


@router.get("/api/influence/community")
def get_community_influence(
    request: Request,
    case_id: Optional[str] = Query(None, description="Optional case ID scope")
) -> Dict[str, Any]:
    """Retrieve community-level influence rankings and group bridge entities (Day 27 + Day 28 integration)."""
    graph = request.app.state.graph
    if case_id:
        case_id = case_id.strip()
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found in knowledge graph store")

    comm_engine = CommunityDetectionEngine(graph)
    intel_engine = NetworkIntelligenceEngine(graph)

    summary = comm_engine.detect_communities(case_id=case_id)
    community_rankings = []

    for comm in summary.communities:
        member_ids = {m.entity_id for m in comm.members}
        ranked_members = intel_engine.rank_entities(scope_entity_ids=member_ids, limit=5)
        community_rankings.append({
            "community_id": comm.community_id,
            "classification": comm.classification,
            "member_count": comm.member_count,
            "top_influencer": ranked_members[0] if ranked_members else None,
            "ranked_members": ranked_members
        })

    return {
        "scope": f"CASE:{case_id}" if case_id else "GLOBAL",
        "total_communities": summary.total_communities,
        "community_influencers": community_rankings,
        "safety_notice": "Community influence metrics indicate network density and structural connectivity. They do NOT establish legal guilt."
    }
