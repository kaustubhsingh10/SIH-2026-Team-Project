"""Timeline and Event Correlation REST API routes for CrimeGraph AI (Day 23).

Provides endpoints for:
- GET /api/events: List and filter events
- GET /api/events/{event_id}: Retrieve event detail
- GET /api/cases/{case_id}/timeline: Chronological event sequence and correlations for a case
- GET /api/entities/{entity_id}/timeline: Chronological timeline for a specific entity
- GET /api/timeline/cross-case: Cross-case timeline and correlation analysis
- GET /api/timeline/correlations: Retrieve deterministic event correlation links
- GET /api/timeline/conflicts: Retrieve detected temporal data conflicts
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.timeline.engine import TimelineCorrelationEngine
from crimegraph.timeline.models import (
    CrossCaseTimelineResponse,
    EventCorrelation,
    InvestigationEvent,
    TemporalConflict,
    TimelineResponse,
)

router = APIRouter(prefix="", tags=["Timeline & Event Correlation"], dependencies=[Depends(get_current_user)])


def get_timeline_engine(request: Request) -> TimelineCorrelationEngine:
    """Helper to get or initialize the timeline correlation engine on app state."""
    graph: KnowledgeGraphStore = request.app.state.graph
    if not hasattr(request.app.state, "timeline_engine") or request.app.state.timeline_engine is None:
        request.app.state.timeline_engine = TimelineCorrelationEngine(store=graph)
    return request.app.state.timeline_engine


@router.get("/api/events", response_model=Dict[str, Any])
def list_events(
    request: Request,
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g. VEHICLE_SIGHTING, CALL_LOG)"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves all normalized investigation events with optional case or type filters."""
    engine = get_timeline_engine(request)
    events = engine.list_events(case_id=case_id, event_type=event_type)

    audit_logger.log(
        action="EVENT_LIST_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        case_id=case_id,
        status=AuditStatus.SUCCESS,
        details={"events_returned": len(events), "event_type": event_type}
    )

    return {
        "events": [e.model_dump() for e in events],
        "total_count": len(events),
        "disclaimer": "Event records represent documented investigative sightings and do not establish legal guilt."
    }


@router.get("/api/events/{event_id}", response_model=Dict[str, Any])
def get_event_detail(
    event_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves full details for a single investigation event."""
    engine = get_timeline_engine(request)
    event = engine.get_event(event_id.strip())

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found in timeline index."
        )

    audit_logger.log(
        action="EVENT_DETAIL_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=event_id,
        status=AuditStatus.SUCCESS
    )

    return event.model_dump()


@router.get("/api/cases/{case_id}/timeline", response_model=TimelineResponse)
def get_case_timeline(
    case_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> TimelineResponse:
    """Returns chronological events and event correlations for a specific case (Day 23)."""
    graph: KnowledgeGraphStore = request.app.state.graph
    case_id = case_id.strip()

    if case_id not in graph.entities:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found."
        )

    engine = get_timeline_engine(request)
    timeline = engine.get_case_timeline(case_id)

    audit_logger.log(
        action="CASE_TIMELINE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        resource_id=case_id,
        status=AuditStatus.SUCCESS,
        details={"events_count": timeline.total_events, "correlations_count": len(timeline.correlations)}
    )

    return timeline


@router.get("/api/entities/{entity_id}/timeline", response_model=TimelineResponse)
def get_entity_timeline(
    entity_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> TimelineResponse:
    """Returns chronological events and activities linked to a specific entity."""
    graph: KnowledgeGraphStore = request.app.state.graph
    entity_id = entity_id.strip()

    if entity_id not in graph.entities:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID '{entity_id}' not found."
        )

    engine = get_timeline_engine(request)
    timeline = engine.get_entity_timeline(entity_id)

    audit_logger.log(
        action="ENTITY_TIMELINE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.ENTITY,
        resource_id=entity_id,
        status=AuditStatus.SUCCESS,
        details={"events_count": timeline.total_events}
    )

    return timeline


@router.get("/api/timeline/cross-case", response_model=CrossCaseTimelineResponse)
def get_cross_case_timeline(
    request: Request,
    cases: str = Query(..., description="Comma-separated case IDs (e.g. CASE_101,CASE_204)"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CrossCaseTimelineResponse:
    """Synthesizes a cross-case chronological timeline and identifies multi-case correlation links."""
    case_list = [c.strip() for c in cases.split(",") if c.strip()]
    if len(case_list) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cross-case timeline requires at least 2 case IDs."
        )

    graph: KnowledgeGraphStore = request.app.state.graph
    for c in case_list:
        if c not in graph.entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{c}' does not exist in knowledge graph."
            )

    engine = get_timeline_engine(request)
    cross_timeline = engine.get_cross_case_timeline(case_list)

    audit_logger.log(
        action="CROSS_CASE_TIMELINE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={"cases": case_list, "events_count": cross_timeline.total_events, "correlations_count": len(cross_timeline.correlations)}
    )

    return cross_timeline


@router.get("/api/timeline/correlations", response_model=Dict[str, Any])
def get_event_correlations(
    request: Request,
    case_id: Optional[str] = Query(None, description="Filter correlations for a case"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves all grounded event correlation links across the knowledge graph."""
    engine = get_timeline_engine(request)
    events = engine.list_events(case_id=case_id)
    correlations = engine.correlate_events(events)

    audit_logger.log(
        action="EVENT_CORRELATIONS_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={"correlations_returned": len(correlations)}
    )

    return {
        "correlations": [c.model_dump() for c in correlations],
        "total_count": len(correlations),
        "disclaimer": "Event correlations are algorithmic investigative leads and do not prove legal causation or guilt."
    }


@router.get("/api/timeline/conflicts", response_model=Dict[str, Any])
def get_temporal_conflicts(
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves detected discrepancies between multi-source timestamp assertions."""
    engine = get_timeline_engine(request)
    conflicts = list(engine._temporal_conflicts.values())

    audit_logger.log(
        action="TEMPORAL_CONFLICTS_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={"conflicts_count": len(conflicts)}
    )

    return {
        "conflicts": [c.model_dump() for c in conflicts],
        "total_count": len(conflicts)
    }
