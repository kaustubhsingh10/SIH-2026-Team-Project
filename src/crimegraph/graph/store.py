"""Knowledge Graph Store for CrimeGraph AI.

Manages entities, relationships, evidence, indexing, validation, and serialization.
"""

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from crimegraph.models.entities import (
    Entity,
    EntityType,
    Person,
    Phone,
    Vehicle,
    Location,
    Organization,
    Account,
    Case,
    Event,
)
from crimegraph.models.relationships import Relationship, RelationshipType
from crimegraph.models.evidence import Evidence
from crimegraph.models.sources import (
    SourceType,
    SourceMetadata,
    ProvenanceRecord,
    SourceConflict,
    ConflictStatus,
)


ENTITY_TYPE_MAP = {
    EntityType.PERSON.value: Person,
    EntityType.PHONE.value: Phone,
    EntityType.VEHICLE.value: Vehicle,
    EntityType.LOCATION.value: Location,
    EntityType.ORGANIZATION.value: Organization,
    EntityType.ACCOUNT.value: Account,
    EntityType.CASE.value: Case,
    EntityType.EVENT.value: Event,
}


class KnowledgeGraphStore:
    """Core knowledge graph storage, indexing, and multi-source provenance engine.
    
    Provides strict validation, relationship connectivity tracking,
    multi-source provenance attestation, conflict tracking,
    and API contract formatted outputs.
    """

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.evidence: Dict[str, Evidence] = {}

        # Multi-Source Layer: Registry, Provenance, and Conflict Tracking
        self.sources: Dict[str, SourceMetadata] = {}
        self._entity_provenance: Dict[str, List[ProvenanceRecord]] = defaultdict(list)
        self._rel_provenance: Dict[str, List[ProvenanceRecord]] = defaultdict(list)
        self._evidence_provenance: Dict[str, List[ProvenanceRecord]] = defaultdict(list)
        self.conflicts: Dict[str, SourceConflict] = {}
        self._source_entities_index: Dict[str, Set[str]] = defaultdict(set)
        self._source_relationships_index: Dict[str, Set[str]] = defaultdict(set)

        # Adjacency indexes for O(1) graph traversal
        # entity_id -> list of relationship_ids
        self._outgoing: Dict[str, List[str]] = defaultdict(list)
        self._incoming: Dict[str, List[str]] = defaultdict(list)
        self._undirected: Dict[str, List[str]] = defaultdict(list)

        # Entity type, case, and evidence indexes
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._case_membership: Dict[str, Set[str]] = defaultdict(set)
        self._evidence_index: Dict[str, Set[str]] = defaultdict(set)
        self._rel_type_index: Dict[str, Set[str]] = defaultdict(set)

        # Performance memoization cache for case subgraphs
        self._subgraph_cache: Dict[str, Dict[str, Any]] = {}

        # Initialize default baseline sources
        self._init_default_sources()

    def _init_default_sources(self) -> None:
        """Initializes canonical baseline data sources."""
        if "SRC_SYNTHETIC_DATASET" not in self.sources:
            self.register_source(SourceMetadata(
                source_id="SRC_SYNTHETIC_DATASET",
                source_type=SourceType.SYNTHETIC_DATASET,
                source_name="Baseline Synthetic Investigation Dataset",
                description="Core SIH 2026 ground-truth synthetic criminal investigation corpus",
                confidence=1.0,
                is_active=True,
                properties={"dataset": "synthetic_data.json", "baseline": True}
            ))
        if "SRC_MANUAL_ENTRY" not in self.sources:
            self.register_source(SourceMetadata(
                source_id="SRC_MANUAL_ENTRY",
                source_type=SourceType.MANUAL_ENTRY,
                source_name="Manual Analyst Entry",
                description="Direct human investigator annotations and manual records",
                confidence=0.95,
                is_active=True,
                properties={"origin": "MANUAL", "curated": True}
            ))

    def add_evidence(self, ev: Union[Evidence, Dict[str, Any]]) -> Evidence:
        """Add an evidence item with validation."""
        if isinstance(ev, dict):
            ev = Evidence(**ev)
        self.evidence[ev.evidence_id] = ev
        self._subgraph_cache.clear()
        return ev

    def add_entity(self, entity: Union[Entity, Dict[str, Any]]) -> Entity:
        """Add an entity to the graph store with validation and indexing."""
        if isinstance(entity, dict):
            raw_type = entity.get("entity_type") or entity.get("type")
            if not raw_type or raw_type not in ENTITY_TYPE_MAP:
                raise ValueError(f"Unknown or missing entity type: {raw_type}")
            model_cls = ENTITY_TYPE_MAP[raw_type]
            entity = model_cls(**entity)

        entity_id = entity.id

        # Clean old type index if updating existing entity
        if entity_id in self.entities:
            old_type = self.entities[entity_id].entity_type
            if old_type in self._type_index:
                self._type_index[old_type].discard(entity_id)

        self.entities[entity_id] = entity
        self._type_index[entity.entity_type].add(entity_id)

        # Index source evidence
        for sid in getattr(entity, "source_ids", []):
            self._evidence_index[sid].add(entity_id)

        # Update case membership if this entity is a Case
        if entity.entity_type == EntityType.CASE.value:
            self._case_membership[entity_id].add(entity_id)

        self._subgraph_cache.clear()
        return entity

    def add_relationship(self, rel: Union[Relationship, Dict[str, Any]]) -> Relationship:
        """Add a relationship edge between two entities with validation."""
        if isinstance(rel, dict):
            rel = Relationship(**rel)

        rel_id = rel.id
        if rel_id in self.relationships:
            self.remove_relationship(rel_id)
        self.relationships[rel_id] = rel

        # Index adjacencies
        self._outgoing[rel.source_id].append(rel_id)
        self._incoming[rel.target_id].append(rel_id)
        self._undirected[rel.source_id].append(rel_id)
        self._undirected[rel.target_id].append(rel_id)

        # Index relationship type
        rel_type_str = rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship)
        self._rel_type_index[rel_type_str].add(rel_id)

        # Index evidence links
        for evid_id in rel.evidence_ids:
            self._evidence_index[evid_id].add(rel_id)

        # Index case involvement
        if rel.relationship == RelationshipType.INVOLVED_IN:
            if rel.target_id in self.entities and self.entities[rel.target_id].entity_type == EntityType.CASE.value:
                self._case_membership[rel.target_id].add(rel.source_id)
            elif rel.source_id in self.entities and self.entities[rel.source_id].entity_type == EntityType.CASE.value:
                self._case_membership[rel.source_id].add(rel.target_id)

        self._subgraph_cache.clear()
        return rel

    def remove_relationship(self, rel_id: str) -> Optional[Relationship]:
        """Remove a relationship edge and update all indexes."""
        rel = self.relationships.pop(rel_id, None)
        if not rel:
            return None

        if rel_id in self._outgoing[rel.source_id]:
            self._outgoing[rel.source_id].remove(rel_id)
        if rel_id in self._incoming[rel.target_id]:
            self._incoming[rel.target_id].remove(rel_id)
        if rel_id in self._undirected[rel.source_id]:
            self._undirected[rel.source_id].remove(rel_id)
        if rel_id in self._undirected[rel.target_id]:
            self._undirected[rel.target_id].remove(rel_id)

        rel_type_str = rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship)
        self._rel_type_index[rel_type_str].discard(rel_id)

        for evid_id in rel.evidence_ids:
            self._evidence_index[evid_id].discard(rel_id)

        self._subgraph_cache.clear()
        return rel

    def remove_entity(self, entity_id: str) -> Optional[Entity]:
        """Remove an entity and all connected relationship edges safely."""
        entity = self.entities.pop(entity_id, None)
        if not entity:
            return None

        old_type = entity.entity_type
        self._type_index[old_type].discard(entity_id)

        for sid in getattr(entity, "source_ids", []):
            self._evidence_index[sid].discard(entity_id)

        self._case_membership.pop(entity_id, None)
        for c_set in self._case_membership.values():
            c_set.discard(entity_id)

        # Remove all attached relationships
        attached_rels = list(self._undirected.get(entity_id, []))
        for rid in attached_rels:
            self.remove_relationship(rid)

        self._outgoing.pop(entity_id, None)
        self._incoming.pop(entity_id, None)
        self._undirected.pop(entity_id, None)
        self._subgraph_cache.clear()
        return entity

    def get_manual_entities(self) -> List[Entity]:
        """Retrieve all entities added manually."""
        return [e for e in self.entities.values() if getattr(e, "origin", "DATASET") == "MANUAL"]

    def get_manual_relationships(self) -> List[Relationship]:
        """Retrieve all relationships added manually."""
        return [r for r in self.relationships.values() if getattr(r, "origin", "DATASET") == "MANUAL"]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by unique ID."""
        return self.entities.get(entity_id)

    def get_relationship(self, rel_id: str) -> Optional[Relationship]:
        """Retrieve a relationship by unique ID."""
        return self.relationships.get(rel_id)

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Retrieve an evidence record by unique ID."""
        return self.evidence.get(evidence_id)

    def get_all_entities(self) -> List[Entity]:
        """Return all entities in the graph."""
        return list(self.entities.values())

    def get_all_relationships(self) -> List[Relationship]:
        """Return all relationships in the graph."""
        return list(self.relationships.values())

    def get_all_evidence(self) -> List[Evidence]:
        """Return all evidence items in the graph."""
        return list(self.evidence.values())

    def get_entities_by_type(self, entity_type: Union[EntityType, str]) -> List[Entity]:
        """Return all entities belonging to a specific EntityType."""
        type_str = entity_type.value if isinstance(entity_type, EntityType) else entity_type
        return [self.entities[eid] for eid in self._type_index.get(type_str, set()) if eid in self.entities]

    def get_relationships_by_type(self, rel_type: Union[RelationshipType, str]) -> List[Relationship]:
        """Return all relationships belonging to a specific RelationshipType."""
        type_str = rel_type.value if isinstance(rel_type, RelationshipType) else rel_type
        return [self.relationships[rid] for rid in self._rel_type_index.get(type_str, set()) if rid in self.relationships]

    def get_entities_by_case(self, case_id: str) -> List[Entity]:
        """Return all entities associated with a specific case."""
        member_ids = self._case_membership.get(case_id, set())
        return [self.entities[eid] for eid in member_ids if eid in self.entities]

    def get_neighbors(
        self,
        entity_id: str,
        direction: str = "undirected"
    ) -> List[Tuple[Relationship, Entity]]:
        """Get connected relationships and neighboring entities.
        
        direction: 'outgoing', 'incoming', or 'undirected'
        """
        results = []
        if direction == "outgoing":
            rel_ids = self._outgoing.get(entity_id, [])
        elif direction == "incoming":
            rel_ids = self._incoming.get(entity_id, [])
        else:
            rel_ids = self._undirected.get(entity_id, [])

        for rid in rel_ids:
            rel = self.relationships.get(rid)
            if not rel:
                continue
            neighbor_id = rel.target_id if rel.source_id == entity_id else rel.source_id
            neighbor = self.entities.get(neighbor_id)
            if neighbor:
                results.append((rel, neighbor))

        return results

    def get_case_subgraph(self, case_id: str) -> Dict[str, Any]:
        """Returns graph data for a case, strictly matching API_CONTRACT.md Section 3:
        
        GET /api/cases/{case_id}/graph
        {
          "nodes": [...],
          "edges": [...]
        }
        """
        if case_id not in self.entities:
            raise KeyError(f"Case {case_id} not found in graph")

        if case_id in self._subgraph_cache:
            return self._subgraph_cache[case_id]

        involved_entity_ids: Set[str] = {case_id}
        case_edges: List[Relationship] = []

        # Find directly connected entities (e.g. INVOLVED_IN, LOCATED_AT)
        for rel, neighbor in self.get_neighbors(case_id, direction="undirected"):
            involved_entity_ids.add(neighbor.id)
            case_edges.append(rel)

        # Expand 1-hop around involved entities to capture phone/vehicle/location details
        extended_ids = set(involved_entity_ids)
        for eid in involved_entity_ids:
            if eid == case_id:
                continue
            for rel, neighbor in self.get_neighbors(eid, direction="undirected"):
                # Do not jump directly to another unrelated Case entity
                if neighbor.entity_type == EntityType.CASE.value and neighbor.id != case_id:
                    continue
                extended_ids.add(neighbor.id)
                if rel not in case_edges:
                    case_edges.append(rel)

        nodes = []
        for eid in extended_ids:
            entity = self.entities[eid]
            node_dict = entity.model_dump()
            nodes.append(node_dict)

        edges = [rel.model_dump() for rel in case_edges]

        subgraph_result = {
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges
        }
        self._subgraph_cache[case_id] = subgraph_result
        return subgraph_result

    def get_stats(self) -> Dict[str, Any]:
        """Return structural metrics and summary statistics of the knowledge graph store."""
        entity_type_counts = {t: len(ids) for t, ids in self._type_index.items()}
        rel_type_counts = {t: len(ids) for t, ids in self._rel_type_index.items()}
        evidence_tiers: Dict[str, int] = defaultdict(int)
        for ev in self.evidence.values():
            evidence_tiers[ev.confidence_tier] += 1

        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "total_evidence": len(self.evidence),
            "entity_types": entity_type_counts,
            "relationship_types": rel_type_counts,
            "evidence_tiers": dict(evidence_tiers)
        }

    def get_entity_details(self, entity_id: str) -> Dict[str, Any]:
        """Returns entity details, relationships, cases, and evidence matching API_CONTRACT.md:
        
        GET /api/entities/{entity_id}
        """
        entity = self.entities.get(entity_id)
        if not entity:
            raise KeyError(f"Entity {entity_id} not found")

        relationships = []
        cases = []
        evidence_list = []
        seen_evidence_ids = set()

        for rel, neighbor in self.get_neighbors(entity_id, direction="undirected"):
            rel_dict = rel.model_dump()
            rel_dict["target_name"] = getattr(neighbor, "name", getattr(neighbor, "title", neighbor.id))
            relationships.append(rel_dict)

            if neighbor.entity_type == EntityType.CASE.value and neighbor.id not in cases:
                cases.append(neighbor.id)

            for evid_id in rel.evidence_ids:
                if evid_id not in seen_evidence_ids:
                    seen_evidence_ids.add(evid_id)
                    ev = self.evidence.get(evid_id)
                    if ev:
                        evidence_list.append(ev.model_dump())

        # Collect evidence directly linked to entity source_ids
        for evid_id in getattr(entity, "source_ids", []):
            if evid_id not in seen_evidence_ids:
                seen_evidence_ids.add(evid_id)
                ev = self.evidence.get(evid_id)
                if ev:
                    evidence_list.append(ev.model_dump())

        entity_dict = entity.model_dump()
        return {
            "id": entity.id,
            "type": entity.entity_type,
            "name": getattr(entity, "name", getattr(entity, "title", entity.id)),
            "details": entity_dict,
            "relationships": relationships,
            "cases": cases,
            "evidence": evidence_list
        }

    def validate_integrity(self) -> Dict[str, Any]:
        """Performs complete integrity verification across the graph:
        
        1. Entities exist and have unique IDs
        2. All relationships reference existing source and target entities
        3. All referenced evidence IDs exist in the evidence catalog
        4. Internal entity references (phone_ids, vehicle_ids, etc.) point to existing entities
        5. Confidence values are in [0.0, 1.0] range
        6. Zero broken references
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Entity validation
        for eid, entity in self.entities.items():
            if entity.entity_type not in ENTITY_TYPE_MAP:
                errors.append(f"Entity {eid} has invalid entity_type: '{entity.entity_type}'")

            if not (0.0 <= getattr(entity, "confidence", 1.0) <= 1.0):
                errors.append(f"Entity {eid} has invalid confidence: {getattr(entity, 'confidence', None)}")

            # Check entity internal references
            for pid in getattr(entity, "phone_ids", []):
                if pid not in self.entities:
                    errors.append(f"Entity {eid} references non-existent phone_id: {pid}")
            for vid in getattr(entity, "vehicle_ids", []):
                if vid not in self.entities:
                    errors.append(f"Entity {eid} references non-existent vehicle_id: {vid}")
            for aid in getattr(entity, "address_ids", []):
                if aid not in self.entities:
                    errors.append(f"Entity {eid} references non-existent address_id: {aid}")
            owner_id = getattr(entity, "owner_id", None)
            if owner_id and owner_id not in self.entities:
                errors.append(f"Entity {eid} references non-existent owner_id: {owner_id}")
            loc_id = getattr(entity, "location_id", None)
            if loc_id and loc_id not in self.entities:
                errors.append(f"Entity {eid} references non-existent location_id: {loc_id}")

            # Check evidence/source references
            for sid in getattr(entity, "source_ids", []):
                if sid.startswith("EVID_") and sid not in self.evidence:
                    warnings.append(f"Entity {eid} references source_id {sid} not in evidence store")

        # 2. Relationship validation
        valid_rel_types = {rt.value for rt in RelationshipType}
        for rid, rel in self.relationships.items():
            rel_val = rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship)
            if rel_val not in valid_rel_types:
                errors.append(f"Relationship {rid} has invalid relationship type: '{rel_val}'")

            if rel.source_id not in self.entities:
                errors.append(f"Relationship {rid} source_id '{rel.source_id}' does not exist in entities")
            if rel.target_id not in self.entities:
                errors.append(f"Relationship {rid} target_id '{rel.target_id}' does not exist in entities")
            if not (0.0 <= rel.confidence <= 1.0):
                errors.append(f"Relationship {rid} confidence '{rel.confidence}' is outside [0.0, 1.0]")

            for evid_id in rel.evidence_ids:
                if evid_id not in self.evidence:
                    errors.append(f"Relationship {rid} references non-existent evidence_id: {evid_id}")

        # 3. Evidence validation
        for evid_id, ev in self.evidence.items():
            if not (0.0 <= ev.confidence <= 1.0):
                errors.append(f"Evidence {evid_id} confidence '{ev.confidence}' is outside [0.0, 1.0]")
            if not ev.source_text.strip():
                warnings.append(f"Evidence {evid_id} has empty source_text")

        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "entity_count": len(self.entities),
            "relationship_count": len(self.relationships),
            "evidence_count": len(self.evidence),
            "errors": errors,
            "warnings": warnings,
        }

    # --------------------------------------------------------------------------
    # MULTI-SOURCE & PROVENANCE MANAGEMENT
    # --------------------------------------------------------------------------

    def register_source(self, source: Union[SourceMetadata, Dict[str, Any]]) -> SourceMetadata:
        """Register or update a data source in the store."""
        if isinstance(source, dict):
            source = SourceMetadata(**source)
        self.sources[source.source_id] = source
        return source

    def get_source(self, source_id: str) -> Optional[SourceMetadata]:
        """Retrieve source metadata by unique ID."""
        return self.sources.get(source_id)

    def list_sources(self) -> List[SourceMetadata]:
        """List all registered data sources."""
        return list(self.sources.values())

    def add_provenance(self, prov: Union[ProvenanceRecord, Dict[str, Any]]) -> ProvenanceRecord:
        """Add a provenance attestation to an entity, relationship, or evidence."""
        if isinstance(prov, dict):
            prov = ProvenanceRecord(**prov)
        
        # Ensure source exists or register default
        if prov.source_id not in self.sources:
            self.register_source(SourceMetadata(
                source_id=prov.source_id,
                source_type=prov.source_type,
                source_name=prov.source_name or prov.source_id,
                confidence=prov.confidence
            ))

        if prov.entity_id:
            if not self._entity_provenance.get(prov.entity_id) and prov.entity_id in self.entities:
                self.get_entity_provenance(prov.entity_id)

            existing = [
                p for p in self._entity_provenance[prov.entity_id]
                if p.source_id == prov.source_id and p.source_record_id == prov.source_record_id
            ]
            if not existing:
                self._entity_provenance[prov.entity_id].append(prov)
            self._source_entities_index[prov.source_id].add(prov.entity_id)

        if prov.relationship_id:
            if not self._rel_provenance.get(prov.relationship_id) and prov.relationship_id in self.relationships:
                self.get_relationship_provenance(prov.relationship_id)

            existing = [
                p for p in self._rel_provenance[prov.relationship_id]
                if p.source_id == prov.source_id and p.source_record_id == prov.source_record_id
            ]
            if not existing:
                self._rel_provenance[prov.relationship_id].append(prov)
            self._source_relationships_index[prov.source_id].add(prov.relationship_id)

        if prov.evidence_id:
            self._evidence_provenance[prov.evidence_id].append(prov)

        return prov

    def get_entity_provenance(self, entity_id: str) -> List[ProvenanceRecord]:
        """Get all provenance attestations for an entity."""
        records = self._entity_provenance.get(entity_id, [])
        if not records and entity_id in self.entities:
            # Generate default provenance record if none explicitly attached
            ent = self.entities[entity_id]
            origin = getattr(ent, "origin", "DATASET")
            src_id = "SRC_MANUAL_ENTRY" if origin == "MANUAL" else "SRC_SYNTHETIC_DATASET"
            src = self.sources.get(src_id)
            if src:
                rec = ProvenanceRecord(
                    source_id=src.source_id,
                    source_type=src.source_type,
                    source_name=src.source_name,
                    entity_id=entity_id,
                    confidence=getattr(ent, "confidence", 1.0),
                    extraction_method="BASELINE_LOAD" if origin == "DATASET" else "MANUAL_ENTRY"
                )
                self._entity_provenance[entity_id].append(rec)
                self._source_entities_index[src_id].add(entity_id)
                records = self._entity_provenance[entity_id]
        return records

    def get_relationship_provenance(self, rel_id: str) -> List[ProvenanceRecord]:
        """Get all provenance attestations for a relationship."""
        records = self._rel_provenance.get(rel_id, [])
        if not records and rel_id in self.relationships:
            rel = self.relationships[rel_id]
            origin = getattr(rel, "origin", "DATASET")
            src_id = "SRC_MANUAL_ENTRY" if origin == "MANUAL" else "SRC_SYNTHETIC_DATASET"
            src = self.sources.get(src_id)
            if src:
                rec = ProvenanceRecord(
                    source_id=src.source_id,
                    source_type=src.source_type,
                    source_name=src.source_name,
                    relationship_id=rel_id,
                    confidence=rel.confidence,
                    extraction_method="BASELINE_LOAD" if origin == "DATASET" else "MANUAL_ENTRY"
                )
                self._rel_provenance[rel_id].append(rec)
                self._source_relationships_index[src_id].add(rel_id)
                records = self._rel_provenance[rel_id]
        return records

    def get_provenance_by_source(self, source_id: str) -> List[ProvenanceRecord]:
        """Return all provenance records originated by a specific source."""
        results = []
        for prov_list in self._entity_provenance.values():
            for p in prov_list:
                if p.source_id == source_id:
                    results.append(p)
        for prov_list in self._rel_provenance.values():
            for p in prov_list:
                if p.source_id == source_id:
                    results.append(p)
        for prov_list in self._evidence_provenance.values():
            for p in prov_list:
                if p.source_id == source_id:
                    results.append(p)
        return results

    def get_entities_by_source(self, source_id: str) -> List[Entity]:
        """Return all entities provided or attested by a specific source."""
        for eid in self.entities:
            self.get_entity_provenance(eid)
        eids = self._source_entities_index.get(source_id, set())
        return [self.entities[eid] for eid in eids if eid in self.entities]

    def get_relationships_by_source(self, source_id: str) -> List[Relationship]:
        """Return all relationships provided or attested by a specific source."""
        for rid in self.relationships:
            self.get_relationship_provenance(rid)
        rids = self._source_relationships_index.get(source_id, set())
        return [self.relationships[rid] for rid in rids if rid in self.relationships]

    def record_conflict(self, conflict: Union[SourceConflict, Dict[str, Any]]) -> SourceConflict:
        """Records a detected multi-source attribute or relationship discrepancy."""
        if isinstance(conflict, dict):
            conflict = SourceConflict(**conflict)
        self.conflicts[conflict.conflict_id] = conflict
        return conflict

    def get_conflicts(
        self,
        target_id: Optional[str] = None,
        status: Optional[Union[ConflictStatus, str]] = None
    ) -> List[SourceConflict]:
        """List recorded source conflicts with optional filtering."""
        res = list(self.conflicts.values())
        if target_id:
            res = [c for c in res if c.target_id == target_id]
        if status:
            stat_val = status.value if hasattr(status, "value") else str(status)
            res = [c for c in res if c.status == stat_val]
        return res

    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: str,
        resolved_value: Optional[Any] = None,
        notes: Optional[str] = None
    ) -> Optional[SourceConflict]:
        """Resolves a detected conflict with an explicit audit strategy."""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return None
        conflict.status = ConflictStatus.RESOLVED.value
        conflict.resolution_strategy = strategy
        conflict.resolved_value = resolved_value
        conflict.notes = notes
        return conflict

    def get_path_provenance(self, path: List[str]) -> List[Dict[str, Any]]:
        """Extracts complete multi-source provenance along a multi-hop graph path."""
        if not path or len(path) < 2:
            return []
        
        path_provenance = []
        for i in range(len(path) - 1):
            src_node = path[i]
            tgt_node = path[i + 1]
            
            # Find connecting relationship(s)
            neighbors = self.get_neighbors(src_node, direction="undirected")
            matching_rels = [r for r, nbr in neighbors if nbr.id == tgt_node]
            
            rel_prov_list = []
            rel_id = None
            rel_type = None
            if matching_rels:
                rel = matching_rels[0]
                rel_id = rel.id
                rel_type = rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship)
                rel_prov_list = [p.model_dump() for p in self.get_relationship_provenance(rel.id)]
            
            src_node_prov = [p.model_dump() for p in self.get_entity_provenance(src_node)]
            tgt_node_prov = [p.model_dump() for p in self.get_entity_provenance(tgt_node)]
            
            path_provenance.append({
                "step": i + 1,
                "source_node": src_node,
                "source_node_provenance": src_node_prov,
                "target_node": tgt_node,
                "target_node_provenance": tgt_node_prov,
                "relationship_id": rel_id,
                "relationship_type": rel_type,
                "relationship_provenance": rel_prov_list
            })
            
        return path_provenance

    def to_dict(self) -> Dict[str, Any]:
        """Export entire knowledge graph state as a serializable dictionary."""
        return {
            "metadata": {
                "version": "1.0",
                "entity_count": len(self.entities),
                "relationship_count": len(self.relationships),
                "evidence_count": len(self.evidence),
                "source_count": len(self.sources),
                "conflict_count": len(self.conflicts)
            },
            "entities": [e.model_dump() for e in self.entities.values()],
            "relationships": [r.model_dump() for r in self.relationships.values()],
            "evidence": [ev.model_dump() for ev in self.evidence.values()],
            "sources": [s.model_dump() for s in self.sources.values()],
            "provenance": {
                "entities": {k: [p.model_dump() for p in v] for k, v in self._entity_provenance.items()},
                "relationships": {k: [p.model_dump() for p in v] for k, v in self._rel_provenance.items()}
            },
            "conflicts": [c.model_dump() for c in self.conflicts.values()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraphStore":
        """Reconstruct a KnowledgeGraphStore from a serialized dictionary."""
        store = cls()
        for ev_data in data.get("evidence", []):
            store.add_evidence(ev_data)
        for ent_data in data.get("entities", []):
            store.add_entity(ent_data)
        for rel_data in data.get("relationships", []):
            store.add_relationship(rel_data)
        
        # Load sources if present
        for src_data in data.get("sources", []):
            store.register_source(src_data)

        # Load provenance if present
        prov_dict = data.get("provenance", {})
        for eid, prov_list in prov_dict.get("entities", {}).items():
            for p in prov_list:
                store.add_provenance(p)
        for rid, prov_list in prov_dict.get("relationships", {}).items():
            for p in prov_list:
                store.add_provenance(p)

        # Load conflicts if present
        for conf_data in data.get("conflicts", []):
            store.record_conflict(conf_data)

        return store

    def ingest_extracted(
        self,
        extraction_response: Any,
        actor_id: str = "SYSTEM"
    ) -> Dict[str, Any]:
        """Ingests structured output from the NLP Extraction Pipeline into KnowledgeGraphStore (Day 22).

        Registers source metadata, records provenance, links entities/relationships,
        and logs conflicts safely without overwriting baseline data.
        """
        source_doc_id = getattr(extraction_response, "source_document_id", getattr(extraction_response, "document_id", "DOC_UNKNOWN"))
        source_id = f"SRC_NLP_{source_doc_id[:30].upper().replace(' ', '_')}"

        if not self.get_source(source_id):
            self.register_source(SourceMetadata(
                source_id=source_id,
                source_type=SourceType.NLP_EXTRACT,
                source_name=f"NLP Extraction ({source_doc_id})",
                confidence=0.85
            ))

        entities_added = 0
        entities_matched = 0
        relationships_added = 0

        # Process entities
        entities = getattr(extraction_response, "entities", [])
        for ent in entities:
            ent_id = getattr(ent, "resolved_id", None) or getattr(ent, "id", None)
            is_new = getattr(ent, "is_new", True)
            ent_type = getattr(ent, "entity_type", "PERSON")
            can_val = getattr(ent, "canonical_value", "")

            if is_new and ent_id and ent_id not in self.entities:
                payload = {
                    "id": ent_id,
                    "entity_type": ent_type,
                    "origin": "NLP_EXTRACT",
                    "confidence": getattr(ent, "confidence", 0.75),
                }
                if ent_type == "PHONE":
                    payload["phone_number"] = can_val
                elif ent_type == "VEHICLE":
                    payload["registration_number"] = can_val
                elif ent_type == "BANK_ACCOUNT":
                    payload["account_number"] = can_val
                elif ent_type == "CASE":
                    payload["case_id"] = can_val
                    payload["title"] = f"Extracted Case {can_val}"
                else:
                    payload["name"] = can_val

                try:
                    self.add_entity(payload)
                    entities_added += 1
                except Exception:
                    entities_matched += 1
            else:
                entities_matched += 1

        # Process relationships
        rels = getattr(extraction_response, "relationships", [])
        for rel in rels:
            rel_id = getattr(rel, "id", None)
            src_id = getattr(rel, "source_entity_id", None)
            tgt_id = getattr(rel, "target_entity_id", None)
            rel_type = getattr(rel, "relationship_type", "RELATED_TO")

            if rel_id and src_id in self.entities and tgt_id in self.entities:
                if rel_id not in self.relationships:
                    rel_payload = {
                        "id": rel_id,
                        "source_id": src_id,
                        "target_id": tgt_id,
                        "relationship": rel_type,
                        "confidence": getattr(rel, "confidence", 0.75),
                        "evidence_ids": [],
                        "origin": "NLP_EXTRACT",
                    }
                    try:
                        self.add_relationship(rel_payload)
                        relationships_added += 1
                    except Exception:
                        pass

        # Process events
        events = getattr(extraction_response, "events", [])
        events_added = 0
        for ev in events:
            ev_id = getattr(ev, "id", None)
            if ev_id and ev_id not in self.entities:
                raw_ts = getattr(ev, "date_raw", getattr(ev, "date_normalised", None))
                ev_payload = {
                    "id": ev_id,
                    "entity_type": "EVENT",
                    "event_type": getattr(ev, "event_type", "EVENT"),
                    "description": getattr(ev, "description", None),
                    "timestamp": getattr(ev, "date_normalised", raw_ts),
                    "origin": "NLP_EXTRACT",
                    "confidence": getattr(ev, "confidence", 0.75),
                    "source_ids": [source_doc_id] if source_doc_id else []
                }
                try:
                    self.add_entity(ev_payload)
                    events_added += 1
                except Exception:
                    pass

        # Record provenance items
        prov_list = getattr(extraction_response, "provenance", [])
        for p in prov_list:
            try:
                p_dict = p.model_dump() if hasattr(p, "model_dump") else dict(p)
                p_rec = ProvenanceRecord(
                    source_id=source_id,
                    source_type=SourceType.NLP_EXTRACT,
                    source_name=f"NLP Extract: {source_doc_id}",
                    source_record_id=source_doc_id,
                    entity_id=p_dict.get("entity_id"),
                    relationship_id=p_dict.get("relationship_id"),
                    confidence=p_dict.get("confidence", 0.75),
                    extraction_method=p_dict.get("extraction_method", "NLP_EXTRACT"),
                    source_text=p_dict.get("source_snippet")
                )
                self.add_provenance(p_rec)
            except Exception:
                pass

        return {
            "source_id": source_id,
            "entities_added": entities_added,
            "entities_matched": entities_matched,
            "relationships_added": relationships_added,
            "events_added": events_added,
        }

    def to_json(self, filepath: Union[str, Path]) -> None:
        """Save graph data to a formatted JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, filepath: Union[str, Path]) -> "KnowledgeGraphStore":
        """Load graph data from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_cypher_script(self) -> str:
        """Generates Neo4j Cypher statements for integration with Shruti's Neo4j pipeline."""
        lines = ["// CrimeGraph Neo4j Ingestion Script", "// Generated automatically by KnowledgeGraphStore", ""]
        
        # Create Entities
        for e in self.entities.values():
            label = e.entity_type
            props = e.model_dump()
            # Clean list properties for Cypher
            props_cypher = ", ".join(f"{k}: {json.dumps(v)}" for k, v in props.items())
            lines.append(f"MERGE (n:{label} {{id: '{e.id}'}}) SET n += {{{props_cypher}}};")

        lines.append("")
        # Create Relationships
        for r in self.relationships.values():
            rel_type = r.relationship.value if hasattr(r.relationship, "value") else str(r.relationship)
            lines.append(
                f"MATCH (a {{id: '{r.source_id}'}}), (b {{id: '{r.target_id}'}}) "
                f"MERGE (a)-[r:{rel_type} {{id: '{r.id}', confidence: {r.confidence}, evidence_ids: {json.dumps(r.evidence_ids)}}}]->(b);"
            )

        return "\n".join(lines)
