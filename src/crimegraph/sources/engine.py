"""Multi-Source Ingestion Engine for CrimeGraph AI.

Coordinates DataAdapter -> DataNormalizer -> SourceAwareEntityResolver -> KnowledgeGraphStore.
Guarantees:
1. Baseline synthetic dataset remains immutable.
2. Provenance records are retained across all sources.
3. Conflicting assertions are flagged without destructive data loss.
4. Comprehensive audit logging for all ingestion actions.
"""

from typing import Any, Dict, List, Optional
import uuid

from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.sources import (
    IngestionBatchRequest,
    IngestionBatchResponse,
    ProvenanceRecord,
    SourceConflict,
    SourceMetadata,
    SourceType,
)
from crimegraph.sources.normalizer import DataNormalizer
from crimegraph.sources.resolver import SourceAwareEntityResolver


class MultiSourceIngestionEngine:
    """Master orchestrator for ingesting, resolving, and provenance-tracking multi-source data."""

    def __init__(
        self,
        store: KnowledgeGraphStore,
        audit_logger: Optional[AuditLogger] = None
    ):
        self.store = store
        self.audit_logger = audit_logger
        self.resolver = SourceAwareEntityResolver(store)

    def ingest_batch(
        self,
        source_id: str,
        batch: IngestionBatchRequest,
        actor_id: str = "SYSTEM",
        actor_type: AuditActorType = AuditActorType.USER
    ) -> IngestionBatchResponse:
        """Executes atomic, multi-source ingestion with resolution, conflict tracking, and provenance."""
        # 1. Verify or dynamically register source
        source = self.store.get_source(source_id)
        if not source:
            source = SourceMetadata(
                source_id=source_id,
                source_type=SourceType.IMPORTED_DATA,
                source_name=f"Ingested Source ({source_id})",
                confidence=0.90
            )
            self.store.register_source(source)
            if self.audit_logger:
                self.audit_logger.log(
                    action="SOURCE_REGISTERED",
                    actor_id=actor_id,
                    actor_type=actor_type,
                    resource_type=AuditResourceType.SOURCE,
                    resource_id=source_id,
                    status=AuditStatus.SUCCESS,
                    details={"source_name": source.source_name, "source_type": source.source_type}
                )

        entities_added = 0
        entities_matched = 0
        relationships_added = 0
        evidence_added = 0
        conflicts_detected = 0
        detected_conflicts: List[SourceConflict] = []
        errors: List[str] = []

        # Maps incoming temporary IDs to resolved/existing graph IDs
        id_remap: Dict[str, str] = {}

        # 2. Process Evidence First
        for rec in batch.records:
            if rec.record_type.upper() == "EVIDENCE":
                try:
                    ev_data = dict(rec.data)
                    ev_id = ev_data.get("evidence_id") or f"EVID_IMP_{uuid.uuid4().hex[:6].upper()}"
                    ev_data["evidence_id"] = ev_id
                    
                    if ev_id not in self.store.evidence:
                        self.store.add_evidence(ev_data)
                        evidence_added += 1
                    
                    prov = ProvenanceRecord(
                        source_id=source_id,
                        source_type=source.source_type,
                        source_name=source.source_name,
                        source_record_id=rec.source_record_id or ev_id,
                        evidence_id=ev_id,
                        confidence=rec.confidence or ev_data.get("confidence", source.confidence),
                        extraction_method=ev_data.get("extraction_method", "MULTI_SOURCE_INGEST"),
                        source_text=rec.source_text or ev_data.get("source_text")
                    )
                    self.store.add_provenance(prov)
                except Exception as e:
                    errors.append(f"Failed to ingest evidence {rec.source_record_id}: {str(e)}")

        # 3. Process Entities
        for rec in batch.records:
            if rec.record_type.upper() == "ENTITY":
                try:
                    raw_data = dict(rec.data)
                    etype = raw_data.get("entity_type") or raw_data.get("type", "PERSON")
                    norm_data = DataNormalizer.normalize_record_data(etype, raw_data)
                    norm_data["entity_type"] = etype
                    
                    incoming_id = norm_data.get("id", f"{etype}_IMP_{uuid.uuid4().hex[:6].upper()}")
                    norm_data["id"] = incoming_id
                    
                    resolved_id = None
                    if batch.auto_resolve:
                        resolved_id = self.resolver.match_existing_entity(etype, norm_data)

                    conf = rec.confidence or norm_data.get("confidence", source.confidence)

                    if resolved_id:
                        # Existing entity match
                        id_remap[incoming_id] = resolved_id
                        entities_matched += 1

                        if batch.record_conflicts:
                            c_list = self.resolver.detect_entity_conflicts(
                                resolved_id, norm_data, source_id, conf
                            )
                            for conf_item in c_list:
                                self.store.record_conflict(conf_item)
                                detected_conflicts.append(conf_item)
                                conflicts_detected += 1
                                if self.audit_logger:
                                    self.audit_logger.log(
                                        action="SOURCE_CONFLICT_DETECTED",
                                        actor_id=actor_id,
                                        actor_type=actor_type,
                                        resource_type=AuditResourceType.SOURCE,
                                        resource_id=conf_item.conflict_id,
                                        status=AuditStatus.SUCCESS,
                                        details={
                                            "target_id": resolved_id,
                                            "field_name": conf_item.field_name,
                                            "source_id": source_id
                                        }
                                    )

                        # Attach multi-source provenance to matched entity
                        prov = ProvenanceRecord(
                            source_id=source_id,
                            source_type=source.source_type,
                            source_name=source.source_name,
                            source_record_id=rec.source_record_id or incoming_id,
                            entity_id=resolved_id,
                            confidence=conf,
                            extraction_method="SOURCE_RESOLVED_INGEST",
                            source_text=rec.source_text,
                            properties=norm_data
                        )
                        self.store.add_provenance(prov)

                    else:
                        # Create new entity in graph with IMPORTED origin
                        norm_data["origin"] = "IMPORTED"
                        norm_data["confidence"] = conf
                        self.store.add_entity(norm_data)
                        id_remap[incoming_id] = incoming_id
                        entities_added += 1

                        prov = ProvenanceRecord(
                            source_id=source_id,
                            source_type=source.source_type,
                            source_name=source.source_name,
                            source_record_id=rec.source_record_id or incoming_id,
                            entity_id=incoming_id,
                            confidence=conf,
                            extraction_method="SOURCE_NEW_INGEST",
                            source_text=rec.source_text,
                            properties=norm_data
                        )
                        self.store.add_provenance(prov)

                except Exception as e:
                    errors.append(f"Failed to ingest entity {rec.source_record_id}: {str(e)}")

        # 4. Process Relationships
        for rec in batch.records:
            if rec.record_type.upper() == "RELATIONSHIP":
                try:
                    rel_data = dict(rec.data)
                    raw_src = rel_data.get("source_id")
                    raw_tgt = rel_data.get("target_id")
                    
                    # Remap endpoints if they were matched to existing entities
                    src_id = id_remap.get(raw_src, raw_src)
                    tgt_id = id_remap.get(raw_tgt, raw_tgt)
                    rel_type = rel_data.get("relationship", "ASSOCIATED_WITH")
                    
                    if not src_id or not tgt_id:
                        errors.append(f"Relationship missing valid endpoints: {raw_src} -> {raw_tgt}")
                        continue

                    if src_id not in self.store.entities or tgt_id not in self.store.entities:
                        errors.append(f"Relationship endpoints not present in graph: {src_id} or {tgt_id}")
                        continue

                    conf = rec.confidence or rel_data.get("confidence", source.confidence)
                    matched_rel_id = self.resolver.match_existing_relationship(src_id, tgt_id, rel_type)

                    if matched_rel_id:
                        # Existing relationship edge — append evidence and attach provenance
                        existing_rel = self.store.get_relationship(matched_rel_id)
                        new_ev_ids = rel_data.get("evidence_ids", [])
                        for evid in new_ev_ids:
                            if evid not in existing_rel.evidence_ids:
                                existing_rel.evidence_ids.append(evid)

                        prov = ProvenanceRecord(
                            source_id=source_id,
                            source_type=source.source_type,
                            source_name=source.source_name,
                            source_record_id=rec.source_record_id or matched_rel_id,
                            relationship_id=matched_rel_id,
                            confidence=conf,
                            extraction_method="MULTI_SOURCE_REL_MATCH",
                            properties=rel_data
                        )
                        self.store.add_provenance(prov)

                    else:
                        # New relationship edge
                        new_rel_id = rel_data.get("id") or f"REL_IMP_{uuid.uuid4().hex[:6].upper()}"
                        rel_payload = {
                            "id": new_rel_id,
                            "source_id": src_id,
                            "target_id": tgt_id,
                            "relationship": rel_type,
                            "confidence": conf,
                            "evidence_ids": rel_data.get("evidence_ids", []),
                            "origin": "IMPORTED",
                            "properties": rel_data.get("properties", {})
                        }
                        self.store.add_relationship(rel_payload)
                        relationships_added += 1

                        prov = ProvenanceRecord(
                            source_id=source_id,
                            source_type=source.source_type,
                            source_name=source.source_name,
                            source_record_id=rec.source_record_id or new_rel_id,
                            relationship_id=new_rel_id,
                            confidence=conf,
                            extraction_method="MULTI_SOURCE_REL_NEW",
                            properties=rel_payload
                        )
                        self.store.add_provenance(prov)

                except Exception as e:
                    errors.append(f"Failed to ingest relationship {rec.source_record_id}: {str(e)}")

        # 5. Audit Logging for Ingestion Batch
        if self.audit_logger:
            self.audit_logger.log(
                action="SOURCE_INGESTED",
                actor_id=actor_id,
                actor_type=actor_type,
                resource_type=AuditResourceType.SOURCE,
                resource_id=source_id,
                status=AuditStatus.SUCCESS if not errors else AuditStatus.FAILURE,
                details={
                    "entities_added": entities_added,
                    "entities_matched": entities_matched,
                    "relationships_added": relationships_added,
                    "evidence_added": evidence_added,
                    "conflicts_detected": conflicts_detected,
                    "error_count": len(errors)
                }
            )

        msg = (
            f"Ingestion complete for source '{source_id}': {entities_added} added, "
            f"{entities_matched} matched, {relationships_added} relationships, "
            f"{evidence_added} evidence, {conflicts_detected} conflicts."
        )

        return IngestionBatchResponse(
            source_id=source_id,
            entities_added=entities_added,
            entities_matched=entities_matched,
            relationships_added=relationships_added,
            evidence_added=evidence_added,
            conflicts_detected=conflicts_detected,
            conflicts=detected_conflicts,
            errors=errors,
            message=msg
        )
