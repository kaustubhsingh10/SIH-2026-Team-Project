"""Data Source Adapters for CrimeGraph AI.

Provides modular adapters to ingest structured records from different source formats:
- Case Record Adapter (FIR, incident notes, case files)
- Intelligence Source Adapter (HUMINT, informant reports, surveillance feeds)
- Manual Entry Adapter (investigator submissions)
- Generic JSON & CSV Import Adapters
"""

from abc import ABC, abstractmethod
import csv
import io
import json
from typing import Any, Dict, List, Optional
import uuid

from crimegraph.models.sources import IngestionRecord, SourceType


class BaseSourceAdapter(ABC):
    """Abstract base class for all source ingestion adapters."""

    @abstractmethod
    def parse(self, raw_content: Any) -> List[IngestionRecord]:
        """Parses raw content into standardized IngestionRecord objects."""
        pass


class JsonImportAdapter(BaseSourceAdapter):
    """Parses JSON structures containing entities, relationships, or evidence lists."""

    def parse(self, raw_content: Any) -> List[IngestionRecord]:
        if isinstance(raw_content, str):
            data = json.loads(raw_content)
        elif isinstance(raw_content, dict):
            data = raw_content
        else:
            raise ValueError("Expected JSON string or dict")

        records = []
        for ent in data.get("entities", []):
            records.append(IngestionRecord(
                record_type="ENTITY",
                data=ent,
                source_record_id=ent.get("id"),
                confidence=ent.get("confidence")
            ))

        for rel in data.get("relationships", []):
            records.append(IngestionRecord(
                record_type="RELATIONSHIP",
                data=rel,
                source_record_id=rel.get("id"),
                confidence=rel.get("confidence")
            ))

        for ev in data.get("evidence", []):
            records.append(IngestionRecord(
                record_type="EVIDENCE",
                data=ev,
                source_record_id=ev.get("evidence_id"),
                confidence=ev.get("confidence")
            ))

        return records


class CaseRecordAdapter(BaseSourceAdapter):
    """Parses structured incident/case records into graph records."""

    def parse(self, raw_content: Any) -> List[IngestionRecord]:
        if isinstance(raw_content, str):
            data = json.loads(raw_content)
        else:
            data = raw_content

        records = []
        case_id = data.get("case_id", f"CASE_{uuid.uuid4().hex[:4].upper()}")
        
        # Add case entity
        case_entity = {
            "id": case_id,
            "entity_type": "CASE",
            "title": data.get("title", f"Case Record {case_id}"),
            "description": data.get("description", ""),
            "status": data.get("status", "OPEN"),
            "confidence": 1.0
        }
        records.append(IngestionRecord(
            record_type="ENTITY",
            data=case_entity,
            source_record_id=case_id
        ))

        # Add suspects/persons involved
        for p in data.get("persons", []):
            pid = p.get("id", f"PERSON_EXT_{uuid.uuid4().hex[:6].upper()}")
            p_data = {
                "id": pid,
                "entity_type": "PERSON",
                "name": p.get("name", "Unknown Person"),
                "aliases": p.get("aliases", []),
                "age": p.get("age"),
                "gender": p.get("gender"),
                "confidence": p.get("confidence", 0.90)
            }
            records.append(IngestionRecord(
                record_type="ENTITY",
                data=p_data,
                source_record_id=pid
            ))

            # Add INVOLVED_IN edge to case
            records.append(IngestionRecord(
                record_type="RELATIONSHIP",
                data={
                    "id": f"REL_CASEREC_{uuid.uuid4().hex[:6].upper()}",
                    "source_id": pid,
                    "target_id": case_id,
                    "relationship": "INVOLVED_IN",
                    "confidence": p.get("confidence", 0.90),
                    "evidence_ids": []
                },
                source_record_id=f"{pid}->{case_id}"
            ))

        # Add phones mentioned
        for ph in data.get("phones", []):
            ph_id = ph.get("id", f"PHONE_EXT_{uuid.uuid4().hex[:6].upper()}")
            records.append(IngestionRecord(
                record_type="ENTITY",
                data={
                    "id": ph_id,
                    "entity_type": "PHONE",
                    "phone_number": ph.get("phone_number"),
                    "confidence": ph.get("confidence", 0.95)
                },
                source_record_id=ph_id
            ))

        return records


class IntelSourceAdapter(BaseSourceAdapter):
    """Parses intelligence briefings, informant tips, and surveillance observations."""

    def parse(self, raw_content: Any) -> List[IngestionRecord]:
        if isinstance(raw_content, str):
            data = json.loads(raw_content)
        else:
            data = raw_content

        records = []
        intel_id = data.get("intel_id", f"INTEL_{uuid.uuid4().hex[:6].upper()}")
        confidence = float(data.get("reliability_score", 0.85))

        # Extracted observation evidence
        ev_id = f"EVID_INTEL_{uuid.uuid4().hex[:6].upper()}"
        ev_data = {
            "evidence_id": ev_id,
            "source_document_id": intel_id,
            "source_text": data.get("summary", "Intelligence observation extract"),
            "extraction_method": "INTELLIGENCE_REPORT",
            "confidence": confidence
        }
        records.append(IngestionRecord(
            record_type="EVIDENCE",
            data=ev_data,
            source_record_id=intel_id,
            confidence=confidence
        ))

        # Extracted entities
        for ent in data.get("entities", []):
            records.append(IngestionRecord(
                record_type="ENTITY",
                data=ent,
                source_record_id=ent.get("id"),
                confidence=confidence,
                source_text=data.get("summary")
            ))

        # Extracted links
        for rel in data.get("relationships", []):
            rel_copy = dict(rel)
            if "evidence_ids" not in rel_copy or not rel_copy["evidence_ids"]:
                rel_copy["evidence_ids"] = [ev_id]
            records.append(IngestionRecord(
                record_type="RELATIONSHIP",
                data=rel_copy,
                source_record_id=rel_copy.get("id"),
                confidence=confidence
            ))

        return records
