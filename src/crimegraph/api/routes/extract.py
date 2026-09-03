"""Document Extraction API routes for CrimeGraph AI (Day 22 NLP Extraction Pipeline).

Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and RBAC / Audit policies.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user, require_analyst
from crimegraph.auth.models import User
from crimegraph.extraction.engine import NLPExtractionEngine
from crimegraph.extraction.models import ExtractionRequest, ExtractionResponse
from crimegraph.graph.store import KnowledgeGraphStore

router = APIRouter(prefix="", tags=["Document Extraction"], dependencies=[Depends(get_current_user)])


@router.post("/api/extract", response_model=Dict[str, Any])
def extract_document(
    payload: ExtractionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Extracts entities, relationships, events, and evidence from raw investigation text (Day 22).

    Integrates with KnowledgeGraphStore, records multi-source provenance, and logs audit events.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investigation text cannot be empty."
        )

    graph: KnowledgeGraphStore = request.app.state.graph
    doc_id = payload.get_document_id()

    # Case validation if case_id provided
    if payload.case_id:
        c_id = payload.case_id.strip()
        if c_id not in graph.entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case '{c_id}' does not exist in knowledge graph."
            )

    # Audit log: extraction started
    audit_logger.log(
        action="EXTRACTION_STARTED",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        resource_id=doc_id,
        case_id=payload.case_id,
        status=AuditStatus.SUCCESS,
        details={"document_id": doc_id, "text_length": len(payload.text)}
    )

    try:
        engine = NLPExtractionEngine(store=graph)
        result: ExtractionResponse = engine.extract(payload)

        # Audit log: extraction completed
        audit_logger.log(
            action="EXTRACTION_COMPLETED",
            actor_id=current_user.username,
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.INVESTIGATION,
            resource_id=doc_id,
            case_id=payload.case_id,
            status=AuditStatus.SUCCESS,
            details={
                "entities_count": len(result.entities),
                "relationships_count": len(result.relationships),
                "conflicts_count": len(result.conflicts)
            }
        )

        return result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log(
            action="EXTRACTION_FAILED",
            actor_id=current_user.username,
            actor_type=AuditActorType.USER,
            resource_type=AuditResourceType.INVESTIGATION,
            resource_id=doc_id,
            status=AuditStatus.FAILURE,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete NLP document extraction."
        )
