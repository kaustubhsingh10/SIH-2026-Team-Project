"""Pydantic models for the Day-22 NLP Extraction Pipeline.

All models follow the established CrimeGraph API conventions and
DATA_SCHEMA.md / API_CONTRACT.md standards.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Confidence tier — deterministic, rule-based (not probabilistic)
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    """Deterministic extraction confidence tier.

    HIGH   – matched by strict regex (phone, vehicle plate, case ID, account).
    MEDIUM – matched by structured pattern (name capitalisation, keyword phrase).
    LOW    – matched by relaxed / fallback heuristic; requires human verification.
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def to_float(cls, level: "ConfidenceLevel") -> float:
        """Maps confidence tier to a representative float for provenance records."""
        return {cls.HIGH: 0.92, cls.MEDIUM: 0.75, cls.LOW: 0.55}[level]


# ---------------------------------------------------------------------------
# Extracted items
# ---------------------------------------------------------------------------

class ExtractedEntity(BaseModel):
    """A single entity extracted from investigative text."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Tentative entity ID (e.g. PERSON_EXT_001)")
    entity_type: str = Field(..., description="Entity type: PERSON, PHONE, VEHICLE, LOCATION, CASE, BANK_ACCOUNT, ORGANIZATION, EVENT, DATE, EVIDENCE")
    raw_value: str = Field(..., description="Exact string matched in source text")
    canonical_value: str = Field(..., description="Normalised/searchable form")
    confidence_tier: ConfidenceLevel = Field(..., description="Deterministic confidence tier")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Float representation of confidence tier")
    extraction_method: str = Field(..., description="Technique used: REGEX, PATTERN, KEYWORD")
    offset_start: Optional[int] = Field(default=None, description="Character offset start in source text")
    offset_end: Optional[int] = Field(default=None, description="Character offset end in source text")
    resolved_id: Optional[str] = Field(default=None, description="Existing graph entity ID if resolved")
    is_new: bool = Field(default=True, description="False when matched to an existing graph entity")
    properties: Dict[str, Any] = Field(default_factory=dict)


class ExtractedRelationship(BaseModel):
    """A relationship between two extracted (or resolved) entities."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: f"REL_EXT_{uuid.uuid4().hex[:6].upper()}")
    source_entity_id: str = Field(..., description="Source entity tentative/resolved ID")
    target_entity_id: str = Field(..., description="Target entity tentative/resolved ID")
    relationship_type: str = Field(..., description="e.g. USES, COMMUNICATES_WITH, OWNS")
    confidence_tier: ConfidenceLevel = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    extraction_method: str = Field(...)
    supporting_text: str = Field(default="", description="Snippet supporting the relationship claim")


class ExtractedEvent(BaseModel):
    """A temporal event or activity extracted from text."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: f"EVENT_EXT_{uuid.uuid4().hex[:6].upper()}")
    event_type: str = Field(default="GENERIC_EVENT")
    description: str = Field(...)
    date_raw: Optional[str] = Field(default=None)
    date_normalised: Optional[str] = Field(default=None, description="ISO 8601 if parseable")
    location_ref: Optional[str] = Field(default=None)
    entity_refs: List[str] = Field(default_factory=list, description="Entity IDs involved")
    confidence_tier: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    supporting_text: str = Field(default="")


class ExtractionConflict(BaseModel):
    """Conflict detected when an extracted value contradicts existing graph data."""
    model_config = ConfigDict(extra="allow")

    conflict_id: str = Field(default_factory=lambda: f"XCONF_{uuid.uuid4().hex[:8].upper()}")
    entity_id: str = Field(..., description="Graph entity ID in conflict")
    field_name: str = Field(..., description="Attribute with conflicting values")
    existing_value: Any = Field(...)
    extracted_value: Any = Field(...)
    extraction_source_id: str = Field(...)
    confidence_tier: ConfidenceLevel = Field(...)
    notes: str = Field(default="Values differ between existing graph record and NLP extraction")


class ExtractionProvenanceRecord(BaseModel):
    """Full provenance chain for one extraction event."""
    model_config = ConfigDict(extra="allow")

    provenance_id: str = Field(
        default_factory=lambda: f"XPROV_{uuid.uuid4().hex[:10].upper()}"
    )
    source_document_id: str
    source_type: str = "NLP_EXTRACT"
    source_name: str = "NLP Extraction Pipeline"
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    extraction_method: str
    confidence_tier: ConfidenceLevel
    confidence: float
    source_snippet: str = Field(default="", description="Raw text snippet that produced this item")
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None
    case_id: Optional[str] = None
    entity_id: Optional[str] = None
    relationship_id: Optional[str] = None


# ---------------------------------------------------------------------------
# API Request / Response
# ---------------------------------------------------------------------------

class ExtractionRequest(BaseModel):
    """Payload for POST /api/extract."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    text: str = Field(..., description="Investigative text to process")
    source_document_id: Optional[str] = Field(default=None, description="Unique identifier of the source document")
    document_id: Optional[str] = Field(default=None, description="Alias for source_document_id for backward compatibility")
    case_id: Optional[str] = Field(default=None, description="Optional case scope for RBAC and graph resolution")

    def get_document_id(self) -> str:
        """Returns the document ID from either field."""
        return (self.source_document_id or self.document_id or f"DOC_{uuid.uuid4().hex[:6].upper()}").strip()


class ExtractionResponse(BaseModel):
    """Structured response from the NLP extraction endpoint."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    source_document_id: str
    document_id: Optional[str] = None
    case_id: Optional[str] = None
    extraction_id: str = Field(
        default_factory=lambda: f"EXT_{uuid.uuid4().hex[:10].upper()}"
    )
    extracted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    events: List[ExtractedEvent] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: List[ExtractionProvenanceRecord] = Field(default_factory=list)
    conflicts: List[ExtractionConflict] = Field(default_factory=list)
    graph_integration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of entities/relationships merged into KnowledgeGraphStore"
    )
    extraction_status: str = Field(default="SUCCESS")
    disclaimer: str = Field(
        default=(
            "CrimeGraph AI NLP extraction produces investigative leads only. "
            "Extracted entities and relationships are NOT proof of criminal guilt. "
            "All leads require independent human verification."
        )
    )
