"""Evidence API routes for CrimeGraph AI.

Strictly adheres to API_CONTRACT.md and DATA_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])


@router.get("", response_model=List[Dict[str, Any]])
def list_evidence(
    request: Request,
    source_document_id: Optional[str] = Query(None, description="Filter by source document ID/filename"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    case_id: Optional[str] = Query(None, description="Filter evidence linked to a specific case")
) -> List[Dict[str, Any]]:
    """List and filter evidence provenance records in the knowledge graph."""
    graph = request.app.state.graph
    all_evidence = graph.get_all_evidence()
    
    if source_document_id:
        all_evidence = [ev for ev in all_evidence if source_document_id.lower() in ev.source_document_id.lower()]
        
    if min_confidence is not None:
        all_evidence = [ev for ev in all_evidence if ev.confidence >= min_confidence]
        
    if case_id:
        if case_id not in graph.entities:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        subgraph = graph.get_case_subgraph(case_id)
        # Collect evidence IDs from case nodes and edges
        case_evid_ids = set()
        for node in subgraph.get("nodes", []):
            case_evid_ids.update(node.get("source_ids", []))
        for edge in subgraph.get("edges", []):
            case_evid_ids.update(edge.get("evidence_ids", []))
        all_evidence = [ev for ev in all_evidence if ev.evidence_id in case_evid_ids]
        
    return [ev.model_dump() for ev in all_evidence]


@router.get("/{evidence_id}")
def get_evidence_item(request: Request, evidence_id: str) -> Dict[str, Any]:
    """Retrieve detailed provenance for a specific evidence item."""
    graph = request.app.state.graph
    ev = graph.get_evidence(evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence with ID '{evidence_id}' not found")
        
    data = ev.model_dump()
    data["confidence_tier"] = ev.confidence_tier
    return data
