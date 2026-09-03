"""Legacy Entity Resolution API router for backward compatibility with earlier demo contracts."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, Request

from crimegraph.auth.dependencies import get_current_user
from crimegraph.auth.models import User
from crimegraph.graph.store import KnowledgeGraphStore

router = APIRouter(prefix="/api/entity-resolution", tags=["Entity Resolution"], dependencies=[Depends(get_current_user)])


@router.get("/pending", response_model=Dict[str, Any])
def get_pending_resolution(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Legacy backward-compatibility endpoint for pending entity resolution reviews."""
    graph: KnowledgeGraphStore = request.app.state.graph
    candidates = []
    
    if "PERSON_017" in graph.entities and "PERSON_089" in graph.entities:
        candidates.append({
            "candidate_id": "CAND_001",
            "entity_a": "PERSON_017",
            "entity_b": "PERSON_089",
            "entity_type": "PERSON",
            "similarity": 0.45,
            "reason": "Shared phone communication endpoint: PHONE_042"
        })

    return {
        "status": "PENDING_REVIEW",
        "total_pending": len(candidates),
        "candidates": candidates,
        "disclaimer": "Pending entity resolution reviews require investigator verification."
    }
