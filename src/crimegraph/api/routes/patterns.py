"""Suspicious Pattern & Anomaly Intelligence API routes for CrimeGraph AI (Day 30).

Provides endpoints to query graph-grounded suspicious relationship patterns,
behavioral anomalies, cross-case bridges, and multi-source corroborations.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and RBAC policies.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.graph.patterns import SuspiciousPatternEngine
from crimegraph.models.patterns import PatternDetectionRequest, PatternQueryResponse

router = APIRouter(prefix="", tags=["Suspicious Patterns"], dependencies=[Depends(get_current_user)])


@router.get("/api/patterns")
def get_suspicious_patterns(
    request: Request,
    case_id: Optional[str] = Query(None, description="Filter patterns by involved case ID"),
    entity_id: Optional[str] = Query(None, description="Filter patterns by involved entity ID"),
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    min_severity: Optional[str] = Query(None, description="Filter by minimum severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter by minimum confidence score"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter by minimum anomaly score"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of patterns to return"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves detected graph-grounded suspicious activity patterns and anomalies."""
    graph = request.app.state.graph
    engine = SuspiciousPatternEngine(graph)

    patterns = engine.detect_all_patterns(
        case_id=case_id,
        entity_id=entity_id,
        pattern_type=pattern_type,
        min_severity=min_severity,
        min_confidence=min_confidence,
        min_score=min_score,
        limit=limit
    )

    audit_logger.log(
        action="PATTERN_DETECTION_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "case_id": case_id,
            "entity_id": entity_id,
            "pattern_type": pattern_type,
            "patterns_found": len(patterns)
        }
    )

    return {
        "patterns": patterns,
        "total_count": len(patterns),
        "limit": limit,
        "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent."
    }


@router.get("/api/patterns/{pattern_id}")
def get_pattern_by_id(
    pattern_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieves detailed information for a specific detected pattern."""
    graph = request.app.state.graph
    engine = SuspiciousPatternEngine(graph)

    patterns = engine.detect_all_patterns(limit=200)
    for pat in patterns:
        if pat.get("pattern_id", "").upper() == pattern_id.upper():
            return {
                "pattern": pat,
                "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent."
            }

    raise HTTPException(status_code=404, detail=f"Pattern ID '{pattern_id}' not found")


@router.post("/api/patterns/detect", response_model=PatternQueryResponse)
def detect_patterns_post(
    request: Request,
    payload: PatternDetectionRequest,
    current_user: User = Depends(get_current_user)
) -> PatternQueryResponse:
    """Executes a fresh pattern detection sweep with custom threshold configuration."""
    graph = request.app.state.graph
    engine = SuspiciousPatternEngine(graph)

    patterns = engine.detect_all_patterns(
        case_id=payload.case_id,
        entity_id=payload.entity_id,
        pattern_type=payload.pattern_type,
        min_score=payload.min_score,
        limit=payload.limit
    )

    return PatternQueryResponse(
        total_patterns=len(patterns),
        patterns=patterns
    )


@router.get("/api/cases/{case_id}/patterns")
def get_case_suspicious_patterns(
    case_id: str,
    request: Request,
    min_severity: Optional[str] = Query(None, description="Filter by minimum severity"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter by minimum confidence"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves suspicious activity patterns associated with a specific case."""
    graph = request.app.state.graph
    case_id = case_id.strip().upper()

    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    engine = SuspiciousPatternEngine(graph)
    patterns = engine.detect_all_patterns(
        case_id=case_id,
        min_severity=min_severity,
        min_confidence=min_confidence
    )

    audit_logger.log(
        action="PATTERN_DETECTION_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.CASE,
        case_id=case_id,
        status=AuditStatus.SUCCESS,
        details={
            "case_id": case_id,
            "patterns_found": len(patterns)
        }
    )

    return {
        "case_id": case_id,
        "patterns": patterns,
        "total_count": len(patterns),
        "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent."
    }


@router.get("/api/entities/{entity_id}/patterns")
def get_entity_suspicious_patterns(
    entity_id: str,
    request: Request,
    min_severity: Optional[str] = Query(None, description="Filter by minimum severity"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter by minimum confidence"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves suspicious activity patterns associated with a specific entity."""
    graph = request.app.state.graph
    entity_id = entity_id.strip().upper()

    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    engine = SuspiciousPatternEngine(graph)
    patterns = engine.detect_all_patterns(
        entity_id=entity_id,
        min_severity=min_severity,
        min_confidence=min_confidence
    )

    return {
        "entity_id": entity_id,
        "patterns": patterns,
        "total_count": len(patterns),
        "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent."
    }
