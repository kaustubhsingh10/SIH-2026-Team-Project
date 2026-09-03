"""Multi-Source Data Models for CrimeGraph AI.

Provides source metadata, provenance tracking, and conflict detection structures.
Strictly adheres to DATA_SCHEMA.md, API_CONTRACT.md, and RBAC policies.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(str, Enum):
    """Enumeration of supported multi-source data origins."""
    SYNTHETIC_DATASET = "SYNTHETIC_DATASET"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    CASE_RECORD = "CASE_RECORD"
    EVIDENCE_RECORD = "EVIDENCE_RECORD"
    INTELLIGENCE_SOURCE = "INTELLIGENCE_SOURCE"
    IMPORTED_DATA = "IMPORTED_DATA"
    NLP_EXTRACT = "NLP_EXTRACT"  # Day 22: entities/relationships from unstructured text
    SOCIAL_MEDIA_SYNTHETIC = "SOCIAL_MEDIA_SYNTHETIC"  # Day 25: simulated/synthetic social media records


class ConflictStatus(str, Enum):
    """Status of a detected data source conflict."""
    DETECTED = "DETECTED"
    RESOLVED = "RESOLVED"
    FLAGGED = "FLAGGED"
    IGNORED = "IGNORED"


class SourceMetadata(BaseModel):
    """Represents a registered data source providing graph entities and relationships."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    source_id: str = Field(..., description="Unique source identifier (e.g. SRC_SYNTHETIC, SRC_CASE_101, SRC_INTEL_01)")
    source_type: SourceType = Field(..., description="Category of data source")
    source_name: str = Field(..., description="Human-readable name of the source")
    description: Optional[str] = Field(default=None, description="Detailed description of the source feed or archive")
    source_record_id: Optional[str] = Field(default=None, description="External record/file identifier if applicable")
    ingested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 ingestion timestamp")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Baseline reliability score for this source")
    is_active: bool = Field(default=True, description="Whether this source is currently active in the graph")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary source metadata (e.g. jurisdiction, agency, format)")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class ProvenanceRecord(BaseModel):
    """Represents an atomic lineage/provenance attestation from a specific source."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    provenance_id: str = Field(default_factory=lambda: f"PROV_{uuid.uuid4().hex[:10].upper()}", description="Unique provenance attestation ID")
    source_id: str = Field(..., description="ID of the registered data source")
    source_type: SourceType = Field(..., description="Type of source")
    source_name: str = Field(..., description="Name of source at time of ingestion")
    source_record_id: Optional[str] = Field(default=None, description="External record or document ID")
    entity_id: Optional[str] = Field(default=None, description="Associated entity ID if attesting an entity")
    relationship_id: Optional[str] = Field(default=None, description="Associated relationship ID if attesting an edge")
    evidence_id: Optional[str] = Field(default=None, description="Linked evidence ID from knowledge graph if available")
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Extraction timestamp")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence of this specific attestation")
    extraction_method: Optional[str] = Field(default="DIRECT_INGEST", description="Method used to extract fact (e.g. AI_NER, MANUAL, CALL_LOG)")
    source_text: Optional[str] = Field(default=None, description="Snippet or raw excerpt from source record")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Field-level values asserted by this source")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class SourceConflict(BaseModel):
    """Represents a discrepancy detected between two or more sources regarding an entity or relationship fact."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    conflict_id: str = Field(default_factory=lambda: f"CONF_{uuid.uuid4().hex[:10].upper()}", description="Unique conflict ID")
    target_type: str = Field(..., description="Target category: ENTITY or RELATIONSHIP")
    target_id: str = Field(..., description="Entity ID or Relationship ID experiencing conflict")
    field_name: str = Field(..., description="Attribute name in conflict (e.g. name, age, phone_number, confidence)")
    source_records: List[Dict[str, Any]] = Field(default_factory=list, description="List of source assertions: [{'source_id': ..., 'value': ..., 'confidence': ...}]")
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Detection timestamp")
    status: ConflictStatus = Field(default=ConflictStatus.DETECTED, description="Current resolution status")
    resolution_strategy: Optional[str] = Field(default=None, description="Resolution strategy if resolved (e.g. MANUAL_OVERRIDE, HIGHEST_CONFIDENCE, RETAIN_BOTH)")
    resolved_value: Optional[Any] = Field(default=None, description="Final resolved value chosen by analyst or rule")
    notes: Optional[str] = Field(default=None, description="Analyst notes explaining resolution or conflict rationale")


# ------------------------------------------------------------------------------
# API DTOs (Request / Response)
# ------------------------------------------------------------------------------

class SourceCreateRequest(BaseModel):
    """Request payload to register a new data source."""
    source_id: str = Field(..., description="Unique source identifier (e.g. SRC_CASE_301, SRC_INTERPOL_INTEL)")
    source_type: SourceType = Field(..., description="Source category")
    source_name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(default=None, description="Detailed source summary")
    source_record_id: Optional[str] = Field(default=None, description="External reference ID")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Source reliability score")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")


class IngestionRecord(BaseModel):
    """Single item to be ingested from a source."""
    model_config = ConfigDict(extra="allow")
    
    record_type: str = Field(..., description="Type of record: ENTITY, RELATIONSHIP, or EVIDENCE")
    data: Dict[str, Any] = Field(..., description="Payload attributes for entity/relationship/evidence")
    source_record_id: Optional[str] = Field(default=None, description="Original record ID in source system")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Record-specific confidence override")
    source_text: Optional[str] = Field(default=None, description="Source excerpt or raw evidence snippet")


class IngestionBatchRequest(BaseModel):
    """Batch payload for ingesting multiple records under a data source."""
    records: List[IngestionRecord] = Field(..., description="List of records to ingest")
    auto_resolve: bool = Field(default=True, description="Whether to automatically match entities against existing graph")
    record_conflicts: bool = Field(default=True, description="Whether to record detected property conflicts")


class IngestionBatchResponse(BaseModel):
    """Result of an ingestion batch operation."""
    source_id: str
    entities_added: int
    entities_matched: int
    relationships_added: int
    evidence_added: int
    conflicts_detected: int
    conflicts: List[SourceConflict] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    message: str


class ConflictResolveRequest(BaseModel):
    """Payload to resolve a detected source conflict."""
    resolution_strategy: str = Field(..., description="Strategy: MANUAL_OVERRIDE, HIGHEST_CONFIDENCE, or RETAIN_BOTH")
    resolved_value: Optional[Any] = Field(default=None, description="Resolved attribute value")
    notes: Optional[str] = Field(default=None, description="Analyst rationale for resolution")
