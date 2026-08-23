"""Relationship models and types for CrimeGraph AI.

Strictly adheres to DATA_SCHEMA.md Section 2 (Relationship Types) and API_CONTRACT.md.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RelationshipType(str, Enum):
    """Enumeration of all allowed relationship types from DATA_SCHEMA.md."""
    # Person -> Person
    CONTACTED = "CONTACTED"
    KNOWS = "KNOWS"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"

    # Person -> Phone / Vehicle
    USES = "USES"
    OWNS = "OWNS"

    # Person -> Location
    VISITED = "VISITED"
    LOCATED_AT = "LOCATED_AT"

    # Person -> Case
    INVOLVED_IN = "INVOLVED_IN"

    # Vehicle -> Location
    SEEN_AT = "SEEN_AT"

    # Person -> Organization
    WORKS_FOR = "WORKS_FOR"

    # Account -> Person
    OWNED_BY = "OWNED_BY"

    # Event -> Person
    INVOLVES = "INVOLVES"

    # Event -> Location
    OCCURRED_AT = "OCCURRED_AT"


class Relationship(BaseModel):
    """Represents a directional edge connecting two entities in the knowledge graph.
    
    Fields defined in DATA_SCHEMA.md and API_CONTRACT.md:
    - id: Unique relationship identifier (e.g. REL_001)
    - source_id: ID of the source entity
    - relationship: Relationship type from DATA_SCHEMA.md (e.g. USES, INVOLVED_IN)
    - target_id: ID of the target entity
    - confidence: Confidence score between 0.0 and 1.0
    - evidence_ids: List of evidence IDs supporting this relationship
    - properties: Optional key-value metadata (e.g. date, call_duration, role)
    """
    id: str = Field(..., description="Unique relationship identifier")
    source_id: str = Field(..., description="Source entity ID")
    relationship: RelationshipType = Field(..., description="Relationship type")
    target_id: str = Field(..., description="Target entity ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting evidence records")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual properties")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)

    @property
    def confidence_tier(self) -> str:
        if self.confidence >= 0.90:
            return "High"
        elif self.confidence >= 0.70:
            return "Medium"
        else:
            return "Low"
