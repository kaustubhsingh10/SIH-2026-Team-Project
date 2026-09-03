"""FastAPI REST API Routes for Day 33 — ML / Data Mining + Investigative Risk Scoring.

Exposes endpoints for entity risk scoring, case-level risk prioritization, ranked priority queues,
and custom risk sweep analytics.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.graph.risk import InvestigativeRiskEngine
from crimegraph.models.risk import (
    CaseRiskResponse,
    EntityRiskResponse,
    RiskAnalyzeRequest,
    RiskPriorityQueryResponse,
)

router = APIRouter(tags=["risk_scoring"])


@router.get("/api/risk/entities/{entity_id}", response_model=EntityRiskResponse)
def get_entity_risk_score(
    entity_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> EntityRiskResponse:
    """Retrieves explainable Investigative Priority Score (0-100) and signal breakdown for an entity."""
    graph = request.app.state.graph
    entity_id = entity_id.strip().upper()

    if entity_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Entity ID '{entity_id}' not found")

    engine = InvestigativeRiskEngine(graph)
    res = engine.calculate_entity_risk(entity_id)

    audit_logger.log(
        action="ENTITY_RISK_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "entity_id": entity_id,
            "risk_score": res.risk_score,
            "risk_level": res.risk_level.value
        }
    )
    return res


@router.get("/api/risk/cases/{case_id}", response_model=CaseRiskResponse)
def get_case_risk_score(
    case_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> CaseRiskResponse:
    """Retrieves case-level investigation risk prioritization and complexity assessment."""
    graph = request.app.state.graph
    case_id = case_id.strip().upper()

    if case_id not in graph.entities:
        raise HTTPException(status_code=404, detail=f"Case ID '{case_id}' not found")

    engine = InvestigativeRiskEngine(graph)
    try:
        res = engine.calculate_case_risk(case_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit_logger.log(
        action="CASE_RISK_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "case_id": case_id,
            "risk_score": res.risk_score,
            "risk_level": res.risk_level.value
        }
    )
    return res


@router.get("/api/risk/priorities", response_model=RiskPriorityQueryResponse)
def get_investigation_priorities(
    request: Request,
    case_id: Optional[str] = Query(None, description="Optional case ID filter (e.g. CASE_101)"),
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    risk_level: Optional[str] = Query(None, description="Optional risk level filter (LOW, MODERATE, HIGH, CRITICAL)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> RiskPriorityQueryResponse:
    """Retrieves ranked investigation priority entities sorted by risk score descending."""
    graph = request.app.state.graph
    engine = InvestigativeRiskEngine(graph)

    if case_id:
        case_id = case_id.strip().upper()
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case ID '{case_id}' not found")

    priorities = engine.get_priorities(
        case_id=case_id,
        min_score=min_score,
        risk_level=risk_level,
        limit=limit
    )

    audit_logger.log(
        action="PRIORITY_RISK_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={
            "case_id": case_id,
            "min_score": min_score,
            "count": len(priorities)
        }
    )

    return RiskPriorityQueryResponse(
        case_filter=case_id,
        min_score=min_score,
        total_count=len(priorities),
        priorities=priorities
    )


@router.post("/api/risk/analyze", response_model=RiskPriorityQueryResponse)
def analyze_risk_sweep(
    payload: RiskAnalyzeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> RiskPriorityQueryResponse:
    """Executes a custom multi-entity risk scoring sweep and investigation ranking."""
    return get_investigation_priorities(
        request=request,
        case_id=payload.case_id,
        min_score=payload.min_score,
        risk_level=None,
        limit=payload.limit,
        current_user=current_user,
        audit_logger=audit_logger
    )
