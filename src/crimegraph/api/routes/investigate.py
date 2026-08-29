"""AI Investigator natural language query API routes for CrimeGraph AI.

Strictly adheres to PROJECT_SPEC.md (F9 — AI Investigator) and Safety Principles.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Header, Request
from crimegraph.graph.traversal import find_cross_case_connections, find_paths_between_entities
from crimegraph.api.routes.auth import verify_bearer_token, verify_case_access

router = APIRouter(prefix="/api/investigate", tags=["AI Investigator"])


class InvestigateRequest(BaseModel):
    question: str = Field(..., description="Natural language investigation query")
    case_id: Optional[str] = Field(None, description="Currently selected case ID context")
    entity_id: Optional[str] = Field(None, description="Currently focused entity ID context")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Prior conversation history")


@router.post("", response_model=Dict[str, Any])
def investigate_query(
    request: Request,
    payload: InvestigateRequest,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Execute a natural-language investigation query grounded in the knowledge graph."""
    user = None
    if authorization:
        user = verify_bearer_token(authorization)
        if payload.case_id:
            verify_case_access(user, payload.case_id)

    graph = getattr(request.app.state, "graph", None)
    if not graph:
        from crimegraph.data.generator import generate_synthetic_investigation_data
        graph = generate_synthetic_investigation_data()

    from crimegraph.ai.investigator import AIInvestigator
    investigator = AIInvestigator(graph)

    try:
        res = investigator.query(
            question=payload.question,
            case_id=payload.case_id,
            entity_id=payload.entity_id,
            conversation_history=payload.conversation_history,
            user=user
        )
    except Exception as err:
        res = {
            "question": payload.question,
            "query_type": "PROVIDER_FAILURE",
            "answer": f"AI Investigation Service encountered an unexpected execution error ({str(err)}). Knowledge graph query terminated safely without generating fabricated data.",
            "confidence": 0.0,
            "path": [],
            "shared_entities": [],
            "evidence": [],
            "explanation": "Query execution aborted due to provider/engine failure.",
            "investigative_lead": "Fallback engaged: Recheck query syntax or perform manual graph inspection.",
            "limitations": ["Automated analysis halted due to runtime execution error."],
            "disclaimer": "Service failure fallback — no fabricated investigation data was generated."
        }

    from crimegraph.api.routes.audit import log_audit_event
    actor_name = user.get("username") if user else "OFFICER_VERMA"
    q_type = res.get("query_type", "GENERAL")
    audit_status = "DENIED" if q_type == "AUTHORIZATION_DENIAL" else ("FAILURE" if q_type in ["SAFETY_REFUSAL", "PROVIDER_FAILURE"] else "SUCCESS")
    
    log_audit_event(
        actor=actor_name,
        action="AI_INVESTIGATION",
        resource_type="AI_QUERY",
        resource_id=payload.question[:30] + ("..." if len(payload.question) > 30 else ""),
        case_id=payload.case_id,
        status=audit_status,
        details={"query_type": q_type, "confidence": res.get("confidence")}
    )

    return res

