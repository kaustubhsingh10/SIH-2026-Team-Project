"""Data models for Cross-Source Intelligence Correlation (Day 32).

Strictly adheres to DATA_SCHEMA.md, API_CONTRACT.md, and Safety Principles.
Guarantees:
- Correlation outputs represent multi-source signal alignments and leads.
- Correlations serve as investigative prioritization signals only, NEVER legal guilt or intent.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CorrelationType(str, Enum):
    """Categories of cross-source intelligence correlation."""
    ENTITY_CORRELATION = "ENTITY_CORRELATION"
    RELATIONSHIP_CORRELATION = "RELATIONSHIP_CORRELATION"
    TEMPORAL_CORRELATION = "TEMPORAL_CORRELATION"
    LOCATION_CORRELATION = "LOCATION_CORRELATION"
    EVENT_CORRELATION = "EVENT_CORRELATION"
    CROSS_CASE_CORRELATION = "CROSS_CASE_CORRELATION"
    CONTRADICTION_DETECTION = "CONTRADICTION_DETECTION"


class CorrelationSeverity(str, Enum):
    """Categorical severity rating of correlated intelligence signals."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CorrelationItem(BaseModel):
    """Explainable cross-source intelligence correlation finding."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    correlation_id: str = Field(..., description="Unique correlation finding ID")
    correlation_type: CorrelationType = Field(..., description="Type of correlation")
    title: str = Field(..., description="Summary title of the correlated signal")
    severity: CorrelationSeverity = Field(default=CorrelationSeverity.MEDIUM, description="Categorical severity rating")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Algorithmic confidence in correlation")
    correlation_score: float = Field(..., ge=0.0, le=1.0, description="Composite explainable score")
    primary_entity_id: Optional[str] = Field(default=None, description="Primary focus entity ID if applicable")
    involved_entity_ids: List[str] = Field(default_factory=list, description="IDs of graph entities involved")
    involved_case_ids: List[str] = Field(default_factory=list, description="IDs of connected cases")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting evidence files/items")
    source_records: List[Dict[str, Any]] = Field(default_factory=list, description="Originating source records")
    scoring_factors: Dict[str, float] = Field(default_factory=dict, description="Factor breakdown powering the composite score")
    explanation: str = Field(..., description="Human-readable investigative justification")
    investigative_lead: str = Field(..., description="Actionable recommendation for human investigators")
    contradiction_details: Optional[str] = Field(default=None, description="Explanation of conflicting signals if present")
    provenance_sources: List[str] = Field(default_factory=list, description="List of source systems (e.g. DATASET, MANUAL, NLP_EXTRACT, SOCIAL)")
    disclaimer: str = Field(
        default="Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt.",
        description="Non-culpability legal disclaimer"
    )


class CorrelationRequest(BaseModel):
    """Request payload for custom correlation detection sweeps."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    case_id: Optional[str] = Field(default=None, description="Filter by case ID")
    entity_id: Optional[str] = Field(default=None, description="Filter by entity ID")
    correlation_type: Optional[CorrelationType] = Field(default=None, description="Filter by correlation category")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum correlation score threshold")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum correlations to return")


class CorrelationQueryResponse(BaseModel):
    """API response model for correlation queries."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    correlations: List[CorrelationItem] = Field(default_factory=list, description="List of detected correlations")
    total_count: int = Field(..., description="Total correlations matching query")
    disclaimer: str = Field(
        default="Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt.",
        description="Non-culpability legal disclaimer"
    )
