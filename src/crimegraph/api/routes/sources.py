"""Multi-Source REST API routes for CrimeGraph AI.

Provides endpoints to query data sources, provenance lineage, ingestion feeds,
conflict tracking, and multi-source path verification.
Strictly adheres to API_CONTRACT.md, DATA_SCHEMA.md, and RBAC policies.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from crimegraph.audit.dependencies import get_audit_logger
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.auth.dependencies import get_current_user, require_analyst
from crimegraph.auth.models import User
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.sources import (
    ConflictResolveRequest,
    ConflictStatus,
    IngestionBatchRequest,
    IngestionBatchResponse,
    ProvenanceRecord,
    SourceConflict,
    SourceCreateRequest,
    SourceMetadata,
)
from crimegraph.sources.engine import MultiSourceIngestionEngine

router = APIRouter(prefix="", tags=["Multi-Source Layer"], dependencies=[Depends(get_current_user)])


@router.get("/api/sources")
def list_data_sources(
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Lists all registered multi-source feeds with entity, relationship, and evidence counts."""
    graph: KnowledgeGraphStore = request.app.state.graph
    sources = graph.list_sources()

    results = []
    for s in sources:
        e_count = len(graph.get_entities_by_source(s.source_id))
        r_count = len(graph.get_relationships_by_source(s.source_id))
        s_dict = s.model_dump()
        s_dict["entity_count"] = e_count
        s_dict["relationship_count"] = r_count
        results.append(s_dict)

    audit_logger.log(
        action="SOURCE_LIST_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.SOURCE,
        status=AuditStatus.SUCCESS,
        details={"sources_returned": len(results)}
    )

    return {
        "sources": results,
        "total_count": len(results),
        "disclaimer": "CrimeGraph AI multi-source records track evidence origin and do not establish legal guilt."
    }


@router.post("/api/sources", status_code=status.HTTP_201_CREATED)
def register_data_source(
    payload: SourceCreateRequest,
    request: Request,
    current_user: User = Depends(require_analyst),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Registers a new data source feed in the knowledge graph. Requires ANALYST or ADMIN role."""
    graph: KnowledgeGraphStore = request.app.state.graph
    src_id = payload.source_id.strip()

    if graph.get_source(src_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Data source '{src_id}' is already registered."
        )

    source = SourceMetadata(
        source_id=src_id,
        source_type=payload.source_type,
        source_name=payload.source_name,
        description=payload.description,
        source_record_id=payload.source_record_id,
        confidence=payload.confidence,
        properties=payload.properties
    )
    graph.register_source(source)

    audit_logger.log(
        action="SOURCE_REGISTERED",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.SOURCE,
        resource_id=src_id,
        status=AuditStatus.SUCCESS,
        details={"source_name": payload.source_name, "source_type": payload.source_type}
    )

    return {
        "source": source.model_dump(),
        "message": f"Data source '{src_id}' registered successfully."
    }


@router.get("/api/sources/conflicts")
def list_source_conflicts(
    request: Request,
    target_id: Optional[str] = Query(None, description="Filter by target entity or relationship ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by conflict status (DETECTED, RESOLVED, FLAGGED)"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Lists detected discrepancies across disparate source feeds for entities or relationships."""
    graph: KnowledgeGraphStore = request.app.state.graph
    conflicts = graph.get_conflicts(target_id=target_id, status=status_filter)

    audit_logger.log(
        action="SOURCE_CONFLICTS_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.SOURCE,
        status=AuditStatus.SUCCESS,
        details={"target_id": target_id, "conflicts_found": len(conflicts)}
    )

    return {
        "conflicts": [c.model_dump() for c in conflicts],
        "total_count": len(conflicts)
    }


@router.post("/api/sources/conflicts/{conflict_id}/resolve")
def resolve_source_conflict(
    conflict_id: str,
    payload: ConflictResolveRequest,
    request: Request,
    current_user: User = Depends(require_analyst),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Resolves a detected source discrepancy with an explicit audit strategy. Requires ANALYST or ADMIN."""
    graph: KnowledgeGraphStore = request.app.state.graph
    resolved = graph.resolve_conflict(
        conflict_id=conflict_id,
        strategy=payload.resolution_strategy,
        resolved_value=payload.resolved_value,
        notes=payload.notes
    )

    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source conflict '{conflict_id}' not found."
        )

    audit_logger.log(
        action="SOURCE_CONFLICT_RESOLVED",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.SOURCE,
        resource_id=conflict_id,
        status=AuditStatus.SUCCESS,
        details={
            "strategy": payload.resolution_strategy,
            "resolved_value": str(payload.resolved_value),
            "target_id": resolved.target_id
        }
    )

    return {
        "conflict": resolved.model_dump(),
        "message": f"Conflict '{conflict_id}' resolved successfully."
    }


@router.get("/api/sources/{source_id}")
def get_data_source_detail(
    source_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves metadata and contribution metrics for a specific data source."""
    graph: KnowledgeGraphStore = request.app.state.graph
    source = graph.get_source(source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source '{source_id}' not found."
        )

    entities = graph.get_entities_by_source(source_id)
    relationships = graph.get_relationships_by_source(source_id)

    audit_logger.log(
        action="SOURCE_DETAIL_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.SOURCE,
        resource_id=source_id,
        status=AuditStatus.SUCCESS
    )

    s_dict = source.model_dump()
    s_dict["entity_count"] = len(entities)
    s_dict["relationship_count"] = len(relationships)
    s_dict["entities"] = [e.id for e in entities]
    s_dict["relationships"] = [r.id for r in relationships]

    return s_dict


@router.post("/api/sources/{source_id}/ingest", response_model=IngestionBatchResponse)
def ingest_source_batch(
    source_id: str,
    batch: IngestionBatchRequest,
    request: Request,
    current_user: User = Depends(require_analyst),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> IngestionBatchResponse:
    """Ingests a batch of records under a source feed with safe entity resolution and conflict tracking."""
    graph: KnowledgeGraphStore = request.app.state.graph
    engine = MultiSourceIngestionEngine(store=graph, audit_logger=audit_logger)

    response = engine.ingest_batch(
        source_id=source_id,
        batch=batch,
        actor_id=current_user.username,
        actor_type=AuditActorType.USER
    )

    return response


@router.get("/api/sources/{source_id}/entities")
def get_source_entities(
    source_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieves all entities attested or originated by a specific data source."""
    graph: KnowledgeGraphStore = request.app.state.graph
    source = graph.get_source(source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source '{source_id}' not found."
        )

    entities = graph.get_entities_by_source(source_id)
    return {
        "source_id": source_id,
        "source_name": source.source_name,
        "total_entities": len(entities),
        "entities": [e.model_dump() for e in entities]
    }


@router.get("/api/entities/{entity_id}/sources")
def get_entity_source_provenance(
    entity_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves all multi-source provenance attestations and discrepancies for a specific entity."""
    graph: KnowledgeGraphStore = request.app.state.graph
    entity = graph.get_entity(entity_id)

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found."
        )

    provenance = graph.get_entity_provenance(entity_id)
    conflicts = graph.get_conflicts(target_id=entity_id)

    audit_logger.log(
        action="ENTITY_PROVENANCE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.ENTITY,
        resource_id=entity_id,
        status=AuditStatus.SUCCESS,
        details={"provenance_count": len(provenance), "conflicts_count": len(conflicts)}
    )

    return {
        "entity_id": entity_id,
        "entity_type": entity.entity_type,
        "name": getattr(entity, "name", getattr(entity, "title", entity.id)),
        "provenance": [p.model_dump() for p in provenance],
        "conflicts": [c.model_dump() for c in conflicts],
        "total_sources": len(set(p.source_id for p in provenance))
    }


@router.get("/api/relationships/{relationship_id}/sources")
def get_relationship_source_provenance(
    relationship_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Retrieves all multi-source provenance attestations for a specific relationship edge."""
    graph: KnowledgeGraphStore = request.app.state.graph
    rel = graph.get_relationship(relationship_id)

    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship '{relationship_id}' not found."
        )

    provenance = graph.get_relationship_provenance(relationship_id)
    conflicts = graph.get_conflicts(target_id=relationship_id)

    audit_logger.log(
        action="RELATIONSHIP_PROVENANCE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.RELATIONSHIP,
        resource_id=relationship_id,
        status=AuditStatus.SUCCESS,
        details={"provenance_count": len(provenance)}
    )

    return {
        "relationship_id": relationship_id,
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "relationship": rel.relationship,
        "provenance": [p.model_dump() for p in provenance],
        "conflicts": [c.model_dump() for c in conflicts],
        "total_sources": len(set(p.source_id for p in provenance))
    }


@router.get("/api/graph/path-provenance")
def get_path_multi_source_provenance(
    request: Request,
    nodes: str = Query(..., description="Comma-separated list of node IDs along the path (e.g. CASE_101,PERSON_017,PHONE_042)"),
    current_user: User = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
) -> Dict[str, Any]:
    """Extracts step-by-step multi-source provenance and evidence links along a traversal path."""
    graph: KnowledgeGraphStore = request.app.state.graph
    node_list = [n.strip() for n in nodes.split(",") if n.strip()]

    if len(node_list) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must contain at least 2 connected nodes."
        )

    for n in node_list:
        if n not in graph.entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node '{n}' in requested path does not exist in knowledge graph."
            )

    provenance_steps = graph.get_path_provenance(node_list)

    audit_logger.log(
        action="PATH_PROVENANCE_QUERY",
        actor_id=current_user.username,
        actor_type=AuditActorType.USER,
        resource_type=AuditResourceType.INVESTIGATION,
        status=AuditStatus.SUCCESS,
        details={"path_length": len(node_list), "steps": len(provenance_steps)}
    )

    return {
        "path": node_list,
        "steps": provenance_steps,
        "total_steps": len(provenance_steps),
        "disclaimer": "Path provenance verifies documented multi-source evidence links and does not establish legal guilt."
    }
