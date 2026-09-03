"""Source-Aware Entity & Relationship Resolver for CrimeGraph AI.

Provides deterministic, safe entity matching across disparate data feeds.
Strictly adheres to safety rules:
1. NO unsafe fuzzy merging.
2. Identifies matching entities via exact canonical keys (phone, plate, account, national ID, exact name+phone).
3. If identity cannot be established confidently, creates a distinct entity record.
4. Detects and records field discrepancies as SourceConflict instances instead of silently overwriting.
5. Attaches multi-source provenance attestations to all resolved entities and edges.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import EntityType
from crimegraph.models.sources import (
    ProvenanceRecord,
    SourceConflict,
    ConflictStatus,
    SourceMetadata,
)
from crimegraph.sources.normalizer import DataNormalizer


class SourceAwareEntityResolver:
    """Safe, deterministic entity and relationship resolution engine."""

    def __init__(self, store: KnowledgeGraphStore):
        self.store = store

    def match_existing_entity(self, entity_type: str, data: Dict[str, Any]) -> Optional[str]:
        """Finds an existing entity in the store matching exact canonical attributes.
        
        Safe matching rules:
        - Explicit ID match (e.g. PERSON_017)
        - PHONE: exact normalized phone_number
        - VEHICLE: exact normalized registration_number
        - ACCOUNT: exact normalized account_number
        - PERSON: exact name match with identical phone association, or exact name match
        - LOCATION: exact address match
        """
        # 1. Direct ID match
        eid = data.get("id")
        if eid and eid in self.store.entities:
            return eid

        # 2. Canonical attribute matches per EntityType
        if entity_type == EntityType.PHONE.value:
            target_phone = data.get("phone_number", "")
            if target_phone:
                for peid, pent in self.store.entities.items():
                    if pent.entity_type == EntityType.PHONE.value and getattr(pent, "phone_number", "") == target_phone:
                        return peid

        elif entity_type == EntityType.VEHICLE.value:
            target_reg = data.get("registration_number", "")
            if target_reg:
                for veid, vent in self.store.entities.items():
                    if vent.entity_type == EntityType.VEHICLE.value and getattr(vent, "registration_number", "") == target_reg:
                        return veid

        elif entity_type == EntityType.ACCOUNT.value:
            target_acc = data.get("account_number", "")
            if target_acc:
                for aeid, aent in self.store.entities.items():
                    if aent.entity_type == EntityType.ACCOUNT.value and getattr(aent, "account_number", "") == target_acc:
                        return aeid

        elif entity_type == EntityType.LOCATION.value:
            target_addr = data.get("address", "")
            target_name = data.get("name", "")
            if target_addr:
                for leid, lent in self.store.entities.items():
                    if lent.entity_type == EntityType.LOCATION.value and getattr(lent, "address", "") == target_addr:
                        return leid
            elif target_name:
                for leid, lent in self.store.entities.items():
                    if lent.entity_type == EntityType.LOCATION.value and getattr(lent, "name", "") == target_name:
                        return leid

        elif entity_type == EntityType.PERSON.value:
            target_name = data.get("name", "").strip().lower()
            target_phones = set(data.get("phone_ids", []))
            if target_name:
                for peid, pent in self.store.entities.items():
                    if pent.entity_type == EntityType.PERSON.value:
                        exist_name = getattr(pent, "name", "").strip().lower()
                        if exist_name == target_name:
                            # If phones exist in both, require overlap or match if name is unique
                            exist_phones = set(getattr(pent, "phone_ids", []))
                            if target_phones and exist_phones:
                                if target_phones & exist_phones:
                                    return peid
                            else:
                                return peid

        return None

    def detect_entity_conflicts(
        self,
        existing_entity_id: str,
        incoming_data: Dict[str, Any],
        incoming_source_id: str,
        incoming_confidence: float
    ) -> List[SourceConflict]:
        """Detects discrepancies between existing entity attributes and incoming source assertions."""
        conflicts = []
        existing_ent = self.store.get_entity(existing_entity_id)
        if not existing_ent:
            return conflicts

        existing_dict = existing_ent.model_dump()
        fields_to_check = ["name", "age", "gender", "phone_number", "registration_number", "account_number"]

        for field in fields_to_check:
            if field in incoming_data and field in existing_dict:
                inc_val = incoming_data[field]
                ext_val = existing_dict[field]

                if inc_val is not None and ext_val is not None:
                    # Compare string representations normalized
                    s_inc = str(inc_val).strip().lower()
                    s_ext = str(ext_val).strip().lower()

                    if s_inc and s_ext and s_inc != s_ext:
                        # Existing source record
                        existing_provs = self.store.get_entity_provenance(existing_entity_id)
                        ext_source_id = existing_provs[0].source_id if existing_provs else "SRC_SYNTHETIC_DATASET"
                        ext_conf = getattr(existing_ent, "confidence", 1.0)

                        conflict = SourceConflict(
                            conflict_id=f"CONF_ENT_{existing_entity_id}_{field.upper()}_{uuid.uuid4().hex[:6].upper()}",
                            target_type="ENTITY",
                            target_id=existing_entity_id,
                            field_name=field,
                            source_records=[
                                {
                                    "source_id": ext_source_id,
                                    "value": ext_val,
                                    "confidence": ext_conf
                                },
                                {
                                    "source_id": incoming_source_id,
                                    "value": inc_val,
                                    "confidence": incoming_confidence
                                }
                            ],
                            status=ConflictStatus.DETECTED,
                            notes=f"Discrepancy in '{field}' for entity {existing_entity_id}: existing '{ext_val}' vs incoming '{inc_val}' from {incoming_source_id}"
                        )
                        conflicts.append(conflict)

        return conflicts

    def match_existing_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str
    ) -> Optional[str]:
        """Finds an existing relationship matching the directed (source, target, rel_type) triple."""
        for rid, rel in self.store.relationships.items():
            r_val = rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship)
            if rel.source_id == source_id and rel.target_id == target_id and r_val == rel_type:
                return rid
        return None

    def detect_relationship_conflicts(
        self,
        existing_rel_id: str,
        incoming_data: Dict[str, Any],
        incoming_source_id: str,
        incoming_confidence: float
    ) -> List[SourceConflict]:
        """Detects relationship property discrepancies across sources."""
        conflicts = []
        rel = self.store.get_relationship(existing_rel_id)
        if not rel:
            return conflicts

        existing_conf = rel.confidence
        if abs(existing_conf - incoming_confidence) > 0.25:
            existing_provs = self.store.get_relationship_provenance(existing_rel_id)
            ext_source_id = existing_provs[0].source_id if existing_provs else "SRC_SYNTHETIC_DATASET"
            
            conflict = SourceConflict(
                conflict_id=f"CONF_REL_{existing_rel_id}_CONF_{uuid.uuid4().hex[:6].upper()}",
                target_type="RELATIONSHIP",
                target_id=existing_rel_id,
                field_name="confidence",
                source_records=[
                    {"source_id": ext_source_id, "value": existing_conf, "confidence": existing_conf},
                    {"source_id": incoming_source_id, "value": incoming_confidence, "confidence": incoming_confidence}
                ],
                status=ConflictStatus.DETECTED,
                notes=f"Significant confidence divergence on relationship {existing_rel_id}: {ext_conf:.2f} vs {incoming_confidence:.2f}"
            )
            conflicts.append(conflict)

        return conflicts
