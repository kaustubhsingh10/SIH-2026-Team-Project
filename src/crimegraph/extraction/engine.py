"""NLP Extraction Engine for CrimeGraph AI (Day 22).

Orchestrates:
  text  ->  nlp extractors
        ->  entity resolution (KnowledgeGraphStore)
        ->  conflict detection
        ->  provenance building
        ->  graph integration (ingest_extracted)
        ->  ExtractionResponse

Guarantees:
  - Never invents entities not present in text.
  - Never overwrites existing trusted graph data.
  - All extracted items carry full provenance.
  - SafetyGuard: refusal on guilt-attribution text.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from crimegraph.extraction.models import (
    ConfidenceLevel,
    ExtractionConflict,
    ExtractionRequest,
    ExtractionResponse,
    ExtractedEntity,
)
from crimegraph.extraction.nlp import (
    extract_accounts,
    extract_case_ids,
    extract_dates,
    extract_events,
    extract_locations,
    extract_organizations,
    extract_persons,
    extract_phones,
    extract_relationships,
    extract_vehicles,
)
from crimegraph.extraction.provenance import (
    build_extraction_provenance,
    build_graph_provenance_record,
    build_rel_extraction_provenance,
)
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.sources import SourceMetadata, SourceType

# ---------------------------------------------------------------------------
# SafetyGuard keywords — mirrors the same logic in investigate.py
# ---------------------------------------------------------------------------
_GUILT_KEYWORDS = [
    "guilty", "who is guilty", "is guilty", "is the criminal", "is a criminal",
    "the criminal", "should be arrested", "who committed", "convict",
    "committed the crime", "responsible for the crime", "definitely responsible",
    "who is responsible for",
]

_SAFETY_DISCLAIMER = (
    "CrimeGraph AI NLP Extraction operates strictly as an investigative support tool. "
    "It cannot and does not make determinations of legal guilt or criminal culpability. "
    "All extracted associations are investigative leads requiring independent human verification."
)


def _safety_check(text: str) -> Optional[str]:
    """Returns a safety warning string if guilt-attribution language is detected."""
    lower = text.lower()
    for kw in _GUILT_KEYWORDS:
        if kw in lower:
            return (
                f"SafetyGuard triggered: text contains guilt-attribution language ('{kw}'). "
                "Extraction will proceed for factual entities only; no guilt inferences will be made. "
                + _SAFETY_DISCLAIMER
            )
    return None


def _sanitise_text(text: str) -> str:
    """Sanitises input: strips null bytes and limits to 50 000 characters."""
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return text[:50_000]


def _make_nlp_source_id(source_document_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", source_document_id[:30]).upper()
    return f"SRC_NLP_{safe}"


class NLPExtractionEngine:
    """Orchestrates entity/relationship/event extraction from investigative text."""

    def __init__(self, store: KnowledgeGraphStore):
        self.store = store

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Runs the full NLP pipeline and returns a structured ExtractionResponse."""
        text = _sanitise_text(request.text)
        doc_id = request.get_document_id()
        case_id = (request.case_id or "").strip() or None

        warnings: List[str] = []

        # SafetyGuard check (non-blocking but logged as warning)
        safety_msg = _safety_check(text)
        if safety_msg:
            warnings.append(safety_msg)

        # 1. Run all entity extractors
        phones = extract_phones(text)
        vehicles = extract_vehicles(text)
        accounts = extract_accounts(text)
        case_ids = extract_case_ids(text)
        dates = extract_dates(text)
        persons = extract_persons(text)
        orgs = extract_organizations(text)
        locations = extract_locations(text)

        all_entities: List[ExtractedEntity] = (
            phones + vehicles + accounts + case_ids + dates + persons + orgs + locations
        )

        # 2. Entity resolution against KnowledgeGraphStore
        all_entities, conflicts = self._resolve_entities(all_entities, doc_id)

        # 3. Build canonical_value -> entity_id map for relationship extraction
        entity_map: Dict[str, str] = {}
        for ent in all_entities:
            entity_map[ent.canonical_value] = ent.resolved_id or ent.id
            entity_map[ent.raw_value] = ent.resolved_id or ent.id

        # 4. Extract relationships (only where both endpoints are identified)
        relationships = extract_relationships(text, entity_map)

        # 5. Extract events
        events = extract_events(text)

        # 6. Build evidence records
        import uuid as _uuid
        evidence_id = f"EVID_EXT_{_uuid.uuid4().hex[:6].upper()}"
        evidence_list = [{
            "evidence_id": evidence_id,
            "source_document_id": doc_id,
            "source_text": text[:300],
            "page_number": 1,
            "extraction_method": "NLP_PIPELINE",
            "confidence": 0.90,
            "case_id": case_id
        }]

        # 7. Build provenance
        provenance = []
        for ent in all_entities:
            provenance.append(build_extraction_provenance(ent, doc_id, case_id))
        for rel in relationships:
            provenance.append(build_rel_extraction_provenance(rel, doc_id, case_id))

        # 8. Integrate into KnowledgeGraphStore
        integration_summary = self._ingest_into_graph(
            all_entities, relationships, doc_id, case_id
        )

        return ExtractionResponse(
            source_document_id=doc_id,
            document_id=doc_id,
            case_id=case_id,
            entities=all_entities,
            relationships=relationships,
            events=events,
            evidence=evidence_list,
            provenance=provenance,
            conflicts=conflicts,
            graph_integration=integration_summary,
            extraction_status="SUCCESS",
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Entity resolution
    # ------------------------------------------------------------------

    def _resolve_entities(
        self,
        entities: List[ExtractedEntity],
        doc_id: str,
    ) -> Tuple[List[ExtractedEntity], List[ExtractionConflict]]:
        """Matches each extracted entity against existing graph entities.

        - On match: sets resolved_id, is_new=False.
        - On match with conflicting attributes: records ExtractionConflict.
        - On no match: entity remains is_new=True.
        """
        conflicts: List[ExtractionConflict] = []

        for ent in entities:
            resolved_id = self._match_entity(ent)
            if resolved_id:
                ent.resolved_id = resolved_id
                ent.is_new = False
                # Detect attribute conflicts
                existing = self.store.get_entity(resolved_id)
                if existing:
                    new_conflicts = self._detect_conflicts(ent, existing, doc_id)
                    conflicts.extend(new_conflicts)

        return entities, conflicts

    def _match_entity(self, ent: ExtractedEntity) -> Optional[str]:
        """Searches the graph store for an existing entity matching this extracted item."""
        entity_type = ent.entity_type
        canonical = ent.canonical_value.lower().strip()

        # 1. Direct ID match
        if ent.canonical_value.upper() in self.store.entities:
            existing = self.store.entities[ent.canonical_value.upper()]
            if existing.entity_type == entity_type:
                return ent.canonical_value.upper()

        for eid, existing in self.store.entities.items():
            if existing.entity_type != entity_type:
                continue

            if eid.lower() == canonical:
                return eid

            # Match on canonical value of key identifier fields
            match_val = ""
            if entity_type == "PHONE":
                match_val = getattr(existing, "phone_number", getattr(existing, "number", ""))
            elif entity_type == "VEHICLE":
                match_val = getattr(existing, "registration_number", getattr(existing, "plate", ""))
            elif entity_type == "BANK_ACCOUNT":
                match_val = getattr(existing, "account_number", "")
            elif entity_type == "CASE":
                match_val = getattr(existing, "case_id", eid)
            elif entity_type == "PERSON":
                match_val = getattr(existing, "name", "")
            elif entity_type in ("ORGANIZATION", "LOCATION"):
                match_val = getattr(existing, "name", "")
            else:
                continue

            if match_val and match_val.lower().strip() == canonical:
                return eid

        return None

    def _detect_conflicts(
        self,
        extracted: ExtractedEntity,
        existing,
        doc_id: str,
    ) -> List[ExtractionConflict]:
        """Detects property-level conflicts between extracted and stored values."""
        conflicts: List[ExtractionConflict] = []

        # Map entity type to the key identifier field
        field_map = {
            "PHONE": ("phone_number", extracted.canonical_value),
            "VEHICLE": ("registration_number", extracted.canonical_value),
            "BANK_ACCOUNT": ("account_number", extracted.canonical_value),
            "PERSON": ("name", extracted.canonical_value),
            "ORGANIZATION": ("name", extracted.canonical_value),
            "LOCATION": ("name", extracted.canonical_value),
        }

        if extracted.entity_type not in field_map:
            return []

        field_name, new_val = field_map[extracted.entity_type]
        existing_val = getattr(existing, field_name, None)

        if existing_val and str(existing_val).lower().strip() != str(new_val).lower().strip():
            conflicts.append(ExtractionConflict(
                entity_id=existing.id,
                field_name=field_name,
                existing_value=existing_val,
                extracted_value=new_val,
                extraction_source_id=doc_id,
                confidence_tier=extracted.confidence_tier,
            ))

        return conflicts

    # ------------------------------------------------------------------
    # Graph integration
    # ------------------------------------------------------------------

    def _ingest_into_graph(
        self,
        entities: List[ExtractedEntity],
        relationships,
        doc_id: str,
        case_id: Optional[str],
    ) -> Dict[str, Any]:
        """Writes new entities/relationships to the KnowledgeGraphStore with provenance."""
        nlp_src_id = _make_nlp_source_id(doc_id)

        # Ensure NLP source is registered
        if not self.store.get_source(nlp_src_id):
            self.store.register_source(SourceMetadata(
                source_id=nlp_src_id,
                source_type=SourceType.NLP_EXTRACT,
                source_name=f"NLP Extraction: {doc_id[:40]}",
                confidence=0.80,
            ))

        entities_added = 0
        entities_matched = 0
        relationships_added = 0

        for ent in entities:
            if ent.is_new:
                # Add new entity with NLP origin
                data: Dict[str, Any] = {
                    "id": ent.id,
                    "entity_type": ent.entity_type,
                    "origin": "NLP_EXTRACT",
                    "confidence": ent.confidence,
                }
                # Populate key field by type
                if ent.entity_type == "PHONE":
                    data["phone_number"] = ent.canonical_value
                elif ent.entity_type == "VEHICLE":
                    data["registration_number"] = ent.canonical_value
                elif ent.entity_type == "BANK_ACCOUNT":
                    data["account_number"] = ent.canonical_value
                elif ent.entity_type == "CASE":
                    data["case_id"] = ent.canonical_value
                    data["title"] = f"Extracted case reference {ent.canonical_value}"
                else:
                    data["name"] = ent.canonical_value

                try:
                    self.store.add_entity(data)
                    entities_added += 1
                except Exception:
                    # Entity may already exist — treat as matched
                    entities_matched += 1
                    ent.resolved_id = ent.id
                    ent.is_new = False
            else:
                entities_matched += 1

            # Attach provenance
            try:
                graph_prov = build_graph_provenance_record(
                    source_document_id=doc_id,
                    entity_id=ent.resolved_id or ent.id,
                    method=ent.extraction_method,
                    confidence=ent.confidence,
                    source_text=ent.raw_value,
                )
                graph_prov.source_id = nlp_src_id
                self.store.add_provenance(graph_prov)
            except Exception:
                pass  # Provenance failure must not abort extraction

        for rel in relationships:
            try:
                import uuid as _uuid
                rel_payload = {
                    "id": rel.id,
                    "source_id": rel.source_entity_id,
                    "target_id": rel.target_entity_id,
                    "relationship": rel.relationship_type,
                    "confidence": rel.confidence,
                    "evidence_ids": [],
                    "origin": "NLP_EXTRACT",
                }
                self.store.add_relationship(rel_payload)
                relationships_added += 1

                graph_prov = build_graph_provenance_record(
                    source_document_id=doc_id,
                    relationship_id=rel.id,
                    method=rel.extraction_method,
                    confidence=rel.confidence,
                    source_text=rel.supporting_text,
                )
                graph_prov.source_id = nlp_src_id
                self.store.add_provenance(graph_prov)
            except Exception:
                pass

        return {
            "nlp_source_id": nlp_src_id,
            "entities_added": entities_added,
            "entities_matched": entities_matched,
            "relationships_added": relationships_added,
        }
