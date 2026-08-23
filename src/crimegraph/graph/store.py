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
    """Core knowledge graph storage and indexing engine.
    
    Provides strict validation, relationship connectivity tracking,
    evidence association, and API contract formatted outputs.
    """

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.evidence: Dict[str, Evidence] = {}

        # Adjacency indexes for O(1) graph traversal
        # entity_id -> list of relationship_ids
        self._outgoing: Dict[str, List[str]] = defaultdict(list)
        self._incoming: Dict[str, List[str]] = defaultdict(list)
        self._undirected: Dict[str, List[str]] = defaultdict(list)

        # Entity type and case indexes
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._case_membership: Dict[str, Set[str]] = defaultdict(set)

    def add_evidence(self, ev: Union[Evidence, Dict[str, Any]]) -> Evidence:
        """Add an evidence item with validation."""
        if isinstance(ev, dict):
            ev = Evidence(**ev)
        self.evidence[ev.evidence_id] = ev
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
        self.entities[entity_id] = entity
        self._type_index[entity.entity_type].add(entity_id)

        # Update case membership if this entity is a Case
        if entity.entity_type == EntityType.CASE.value:
            self._case_membership[entity_id].add(entity_id)

        return entity

    def add_relationship(self, rel: Union[Relationship, Dict[str, Any]]) -> Relationship:
        """Add a relationship edge between two entities with validation."""
        if isinstance(rel, dict):
            rel = Relationship(**rel)

        rel_id = rel.id
        self.relationships[rel_id] = rel

        # Index adjacencies
        self._outgoing[rel.source_id].append(rel_id)
        self._incoming[rel.target_id].append(rel_id)
        self._undirected[rel.source_id].append(rel_id)
        self._undirected[rel.target_id].append(rel_id)

        # Index case involvement
        if rel.relationship == RelationshipType.INVOLVED_IN:
            if rel.target_id in self.entities and self.entities[rel.target_id].entity_type == EntityType.CASE.value:
                self._case_membership[rel.target_id].add(rel.source_id)
            elif rel.source_id in self.entities and self.entities[rel.source_id].entity_type == EntityType.CASE.value:
                self._case_membership[rel.source_id].add(rel.target_id)

        return rel

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

        return {
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges
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
        for rid, rel in self.relationships.items():
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

    def to_dict(self) -> Dict[str, Any]:
        """Export entire knowledge graph state as a serializable dictionary."""
        return {
            "metadata": {
                "version": "1.0",
                "entity_count": len(self.entities),
                "relationship_count": len(self.relationships),
                "evidence_count": len(self.evidence)
            },
            "entities": [e.model_dump() for e in self.entities.values()],
            "relationships": [r.model_dump() for r in self.relationships.values()],
            "evidence": [ev.model_dump() for ev in self.evidence.values()]
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
        return store

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
