"""Provenance record builder for the NLP Extraction Pipeline (Day 22).

Constructs ExtractionProvenanceRecord objects from extracted items and
also builds the standard ProvenanceRecord objects expected by KnowledgeGraphStore.
"""

from datetime import datetime, timezone
from typing import Optional

from crimegraph.extraction.models import (
    ConfidenceLevel,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionProvenanceRecord,
)
from crimegraph.models.sources import ProvenanceRecord, SourceType


_NLP_SOURCE_NAME = "NLP Extraction Pipeline (Day 22)"


def build_extraction_provenance(
    item: ExtractedEntity,
    source_document_id: str,
    case_id: Optional[str] = None,
) -> ExtractionProvenanceRecord:
    """Builds an ExtractionProvenanceRecord for an extracted entity."""
    raw_snippet = item.raw_value[:300]
    return ExtractionProvenanceRecord(
        source_document_id=source_document_id,
        source_type="NLP_EXTRACT",
        source_name=_NLP_SOURCE_NAME,
        extraction_method=item.extraction_method,
        confidence_tier=item.confidence_tier,
        confidence=item.confidence,
        source_snippet=raw_snippet,
        offset_start=item.offset_start,
        offset_end=item.offset_end,
        case_id=case_id,
        entity_id=item.resolved_id or item.id,
    )


def build_rel_extraction_provenance(
    rel: ExtractedRelationship,
    source_document_id: str,
    case_id: Optional[str] = None,
) -> ExtractionProvenanceRecord:
    """Builds an ExtractionProvenanceRecord for an extracted relationship."""
    return ExtractionProvenanceRecord(
        source_document_id=source_document_id,
        source_type="NLP_EXTRACT",
        source_name=_NLP_SOURCE_NAME,
        extraction_method=rel.extraction_method,
        confidence_tier=rel.confidence_tier,
        confidence=rel.confidence,
        source_snippet=rel.supporting_text[:300],
        case_id=case_id,
        relationship_id=rel.id,
    )


def build_graph_provenance_record(
    source_document_id: str,
    entity_id: Optional[str] = None,
    relationship_id: Optional[str] = None,
    method: str = "NLP_REGEX",
    confidence: float = 0.75,
    source_text: Optional[str] = None,
) -> ProvenanceRecord:
    """Builds a KnowledgeGraphStore-compatible ProvenanceRecord for NLP-extracted items."""
    return ProvenanceRecord(
        source_id=f"SRC_NLP_{source_document_id[:20].upper().replace(' ', '_')}",
        source_type=SourceType.NLP_EXTRACT,
        source_name=_NLP_SOURCE_NAME,
        source_record_id=source_document_id,
        entity_id=entity_id,
        relationship_id=relationship_id,
        confidence=min(max(round(confidence, 4), 0.0), 1.0),
        extraction_method=method,
        source_text=(source_text or "")[:500],
    )
