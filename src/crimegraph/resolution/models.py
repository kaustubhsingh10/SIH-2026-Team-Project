"""Data Models for Advanced Entity Resolution & Identity Linking (Day 26).

Strictly adheres to DATA_SCHEMA.md, API_CONTRACT.md, and RBAC rules.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class MatchTier(str, Enum):
    """Confidence tier for candidate identity matches."""
    HIGH = "HIGH"          # >= 0.85 (Strong multi-attribute or unique canonical key match)
    MEDIUM = "MEDIUM"      # 0.60 - 0.84 (Probable match requiring officer review)
    LOW = "LOW"            # 0.30 - 0.59 (Weak structural similarity)
    NO_MATCH = "NO_MATCH"  # < 0.30 (Distinct entity)


class IdentityConflictSeverity(str, Enum):
    """Severity of an identity conflict."""
    HIGH = "HIGH"          # Contradictory primary attributes (e.g. conflicting phone/DOB/identity)
    MEDIUM = "MEDIUM"      # Discrepancy in secondary attributes (e.g. alias spelling, location history)
    LOW = "LOW"            # Formatting or minor naming variance


class CandidateMatch(BaseModel):
    """Represents a potential identity match between two entities/records."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    match_id: str = Field(default_factory=lambda: f"MATCH_{uuid.uuid4().hex[:8].upper()}")
    source_entity_id: str = Field(..., description="Entity ID being evaluated")
    target_entity_id: str = Field(..., description="Candidate matching entity ID in KnowledgeGraphStore")
    entity_type: str = Field(..., description="Target entity type (PERSON, PHONE, VEHICLE, etc.)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Calculated matching confidence [0.0 - 1.0]")
    match_tier: MatchTier = Field(..., description="Categorical confidence tier (HIGH, MEDIUM, LOW, NO_MATCH)")
    matched_attributes: List[str] = Field(default_factory=list, description="Attributes supporting the match (e.g. phone_number, name, aliases)")
    explanation: str = Field(..., description="Explainable rationale detailing why these entities were linked")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="Evidence items corroborating this candidate match")
    source_provenance_ids: List[str] = Field(default_factory=list, description="Source provenance IDs associated with matching records")
    has_conflicts: bool = Field(default=False, description="Whether unresolved attribute contradictions exist between records")


class IdentityConflict(BaseModel):
    """Represents a detected identity contradiction that halts automatic merge."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    conflict_id: str = Field(default_factory=lambda: f"IDCONF_{uuid.uuid4().hex[:8].upper()}")
    entity_id_a: str = Field(..., description="First entity involved in contradiction")
    entity_id_b: str = Field(..., description="Second entity or record involved in contradiction")
    attribute_name: str = Field(..., description="Attribute under contradiction (e.g. phone_owner, primary_location)")
    value_a: Any = Field(..., description="Value asserted by source A")
    value_b: Any = Field(..., description="Value asserted by source B")
    source_a_id: str = Field(..., description="Source ID asserting value A")
    source_b_id: str = Field(..., description="Source ID asserting value B")
    severity: IdentityConflictSeverity = Field(default=IdentityConflictSeverity.HIGH)
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    investigative_lead: str = Field(default="Requires human review before identity merge.", description="Actionable recommendation for investigators")
    status: str = Field(default="UNRESOLVED", description="UNRESOLVED, RESOLVED, or FLAGGED")


class EntityMergeRequest(BaseModel):
    """Request payload to merge two candidate entities into a canonical representation."""
    canonical_entity_id: str = Field(..., description="Target canonical entity ID to retain")
    merge_entity_id: str = Field(..., description="Entity ID to merge into the canonical entity")
    reason: str = Field(..., description="Investigative rationale for merging")
    override_conflicts: bool = Field(default=False, description="Explicit authorization to merge despite flagged attribute conflicts")


class EntityMergeResponse(BaseModel):
    """Result of an entity merge operation."""
    canonical_entity_id: str
    merged_entity_id: str
    aliases_retained: List[str] = Field(default_factory=list)
    relationships_migrated: int = 0
    evidence_migrated: int = 0
    provenance_records_retained: int = 0
    status: str = "MERGED"
    merged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    explanation: str


class ResolutionEvaluationRequest(BaseModel):
    """Request payload to evaluate candidate identity matches for a given entity or record."""
    entity_type: str = Field(..., description="PERSON, PHONE, VEHICLE, LOCATION, ACCOUNT, ORGANIZATION")
    attributes: Dict[str, Any] = Field(..., description="Attributes to match against the graph")
    entity_id: Optional[str] = Field(default=None, description="Optional existing entity ID if re-evaluating")
    min_confidence: float = Field(default=0.60, ge=0.0, le=1.0)
