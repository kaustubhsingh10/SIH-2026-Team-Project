"""Community & Criminal Group Detection REST API Endpoints for CrimeGraph AI (Day 27).

Provides endpoints to discover graph communities, query specific clusters,
and analyze case-scoped community structures.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and RBAC policies.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.communities.engine import CommunityDetectionEngine
from crimegraph.communities.models import CommunityDetectionSummary, DetectedCommunity
from crimegraph.graph.store import KnowledgeGraphStore

router = APIRouter(tags=["Communities"], dependencies=[Depends(get_current_user)])


def _get_community_engine(request: Request) -> CommunityDetectionEngine:
    if not hasattr(request.app.state, "community_engine") or request.app.state.community_engine is None:
        graph: KnowledgeGraphStore = request.app.state.graph
        request.app.state.community_engine = CommunityDetectionEngine(graph)
    return request.app.state.community_engine


@router.get("/api/communities", response_model=CommunityDetectionSummary)
def list_graph_communities(
    request: Request,
    min_cluster_size: int = Query(3, ge=2, le=50, description="Minimum entities required to form a cluster"),
    case_id: Optional[str] = Query(None, description="Optional case ID to scope community detection"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CommunityDetectionSummary:
    """Discovers and characterizes all topological graph communities across the knowledge graph."""
    engine = _get_community_engine(request)
    try:
        summary = engine.detect_communities(case_id=case_id, min_cluster_size=min_cluster_size)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    audit_logger.log(
        action="COMMUNITIES_DETECT_GLOBAL",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={"total_communities": summary.total_communities, "case_filter": case_id}
    )

    return summary


@router.get("/api/communities/{community_id}", response_model=DetectedCommunity)
def get_community_detail(
    community_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> DetectedCommunity:
    """Retrieves deep structural metrics and explainable leads for a specific detected community."""
    engine = _get_community_engine(request)
    community = engine.get_community_by_id(community_id)
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Community '{community_id}' not found."
        )

    audit_logger.log(
        action="COMMUNITY_DETAIL_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=community_id,
        status=AuditStatus.SUCCESS,
        details={"member_count": community.member_count, "classification": community.classification}
    )

    return community


@router.get("/api/cases/{case_id}/communities", response_model=CommunityDetectionSummary)
def get_case_communities(
    case_id: str,
    request: Request,
    min_cluster_size: int = Query(2, ge=2, le=50),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CommunityDetectionSummary:
    """Detects and characterizes communities scoped within a specific case investigation."""
    graph: KnowledgeGraphStore = request.app.state.graph
    if case_id not in graph.entities:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found in knowledge graph."
        )

    engine = _get_community_engine(request)
    summary = engine.detect_communities(case_id=case_id, min_cluster_size=min_cluster_size)

    audit_logger.log(
        action="CASE_COMMUNITIES_DETECT",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        resource_id=case_id,
        status=AuditStatus.SUCCESS,
        details={"total_communities": summary.total_communities}
    )

    return summary
