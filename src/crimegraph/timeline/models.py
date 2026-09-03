"""Data models for Day 23: Timeline & Event Correlation Engine.

Strictly follows DATA_SCHEMA.md, API_CONTRACT.md, and RBAC / provenance standards.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TemporalPrecision(str, Enum):
    """Enumeration of temporal precision tiers."""
    EXACT_TIMESTAMP = "EXACT_TIMESTAMP"  # e.g., 2026-08-11T14:30:00Z
    DATE_ONLY = "DATE_ONLY"              # e.g., 2026-08-11
    TIME_RANGE = "TIME_RANGE"            # e.g., 2026-08-11T10:00:00 to 2026-08-11T12:00:00
    APPROXIMATE = "APPROXIMATE"          # e.g., mid-August 2026, yesterday evening
    UNKNOWN = "UNKNOWN"                  # timestamp missing / unstated


class CorrelationType(str, Enum):
    """Reason or basis for correlating two or more investigation events."""
    SHARED_ENTITY = "SHARED_ENTITY"
    SHARED_DEVICE = "SHARED_DEVICE"
    SHARED_VEHICLE = "SHARED_VEHICLE"
    SHARED_LOCATION = "SHARED_LOCATION"
    SHARED_ACCOUNT = "SHARED_ACCOUNT"
    SHARED_CASE = "SHARED_CASE"
    TEMPORAL_PROXIMITY = "TEMPORAL_PROXIMITY"
    CROSS_CASE_BRIDGE = "CROSS_CASE_BRIDGE"
    EVIDENCE_LINKAGE = "EVIDENCE_LINKAGE"


class CorrelationConfidence(str, Enum):
    """Confidence tier for an event correlation link."""
    DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"
    POTENTIAL_CORRELATION = "POTENTIAL_CORRELATION"


class InvestigationEvent(BaseModel):
    """Normalized Investigation Event for Timeline & Correlation."""
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    event_id: str = Field(..., description="Unique event identifier (e.g. EVENT_101_01)")
    id: Optional[str] = Field(default=None, description="Alias for event_id to support API_CONTRACT.md schema compatibility")
    case_id: Optional[str] = Field(default=None, description="Linked case ID if known")
    event_type: str = Field(..., description="Type of event (e.g. VEHICLE_SIGHTING, CALL_LOG, TRANSACTION, RAID)")
    type: Optional[str] = Field(default=None, description="Alias for event_type to support API_CONTRACT.md schema compatibility")
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 timestamp or normalized date")
    timestamp_precision: TemporalPrecision = Field(default=TemporalPrecision.UNKNOWN, description="Precision tier of the timestamp")
    time_range_start: Optional[str] = Field(default=None, description="Start time if precision is TIME_RANGE")
    time_range_end: Optional[str] = Field(default=None, description="End time if precision is TIME_RANGE")
    raw_timestamp: Optional[str] = Field(default=None, description="Original unparsed timestamp string from source")
    location_id: Optional[str] = Field(default=None, description="Location ID where event occurred")
    location_name: Optional[str] = Field(default=None, description="Human readable location name")
    involved_entity_ids: List[str] = Field(default_factory=list, description="IDs of all persons, phones, vehicles, etc. involved")
    relationship_ids: List[str] = Field(default_factory=list, description="IDs of graph relationships active in this event")
    evidence_ids: List[str] = Field(default_factory=list, description="Linked evidence IDs")
    source_document_id: Optional[str] = Field(default=None, description="Document ID or record ID of origin")
    source_type: str = Field(default="SYNTHETIC_DATASET", description="Source category")
    description: Optional[str] = Field(default=None, description="Human-readable event summary")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Extraction / factual confidence")
    confidence_tier: str = Field(default="HIGH", description="HIGH, MEDIUM, LOW")
    extraction_method: Optional[str] = Field(default="DIRECT_RECORD", description="Method used to extract this event")
    provenance_id: Optional[str] = Field(default=None, description="Linked ProvenanceRecord ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary event metadata")

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            self.id = self.event_id
        if not self.type:
            self.type = self.event_type

    @field_validator("confidence")
    @classmethod
    def validate_conf(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class EventCorrelation(BaseModel):
    """Represents a deterministic correlation link between two investigation events."""
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    correlation_id: str = Field(default_factory=lambda: f"CORR_{uuid.uuid4().hex[:8].upper()}")
    source_event_id: str = Field(..., description="First event ID")
    target_event_id: str = Field(..., description="Second event ID")
    correlation_type: CorrelationType = Field(..., description="Primary reason for correlation")
    correlation_confidence: CorrelationConfidence = Field(default=CorrelationConfidence.DIRECTLY_SUPPORTED)
    time_delta_seconds: Optional[float] = Field(default=None, description="Difference in seconds between events if timestamps exist")
    shared_entities: List[str] = Field(default_factory=list, description="Shared entity IDs connecting the events")
    shared_cases: List[str] = Field(default_factory=list, description="Shared case IDs")
    explanation: str = Field(..., description="Detailed explanation of WHY these two events are correlated")
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    disclaimer: str = Field(default="Event correlations are algorithmic investigative leads and do not prove legal causation or guilt.")


class TemporalConflict(BaseModel):
    """Represents conflicting temporal assertions between different sources regarding an event or entity activity."""
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    conflict_id: str = Field(default_factory=lambda: f"TCONF_{uuid.uuid4().hex[:8].upper()}")
    event_id: Optional[str] = Field(default=None, description="Event ID in conflict if applicable")
    entity_id: Optional[str] = Field(default=None, description="Entity ID involved in conflicting activity")
    source_claims: List[Dict[str, Any]] = Field(default_factory=list, description="List of source assertions: [{'source_id': ..., 'timestamp': ..., 'confidence': ...}]")
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = Field(default="DETECTED", description="DETECTED, RESOLVED, FLAGGED")
    discrepancy_description: str = Field(..., description="Description of the timing mismatch")
    human_verification_required: bool = Field(default=True)
    notes: Optional[str] = Field(default=None)


class TimelineResponse(BaseModel):
    """Response payload for Case or Entity Timeline queries."""
    model_config = ConfigDict(extra="allow")

    case_id: Optional[str] = None
    entity_id: Optional[str] = None
    total_events: int
    events: List[InvestigationEvent]
    correlations: List[EventCorrelation] = Field(default_factory=list)
    conflicts: List[TemporalConflict] = Field(default_factory=list)
    time_span: Dict[str, Optional[str]] = Field(default_factory=lambda: {"earliest": None, "latest": None})
    disclaimer: str = Field(default="Timelines present documented investigative event sequences and do not establish legal guilt.")


class CrossCaseTimelineResponse(BaseModel):
    """Response payload for multi-case chronological timeline and correlation queries."""
    model_config = ConfigDict(extra="allow")

    cases: List[str]
    total_events: int
    events: List[InvestigationEvent]
    correlations: List[EventCorrelation] = Field(default_factory=list)
    cross_case_bridge_events: List[InvestigationEvent] = Field(default_factory=list)
    conflicts: List[TemporalConflict] = Field(default_factory=list)
    disclaimer: str = Field(default="Cross-case timelines synthesize multi-source records and do not establish legal guilt.")
