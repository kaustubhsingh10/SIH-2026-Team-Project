"""Data Models for Community & Criminal Group Detection (Day 27).

Strictly adheres to DATA_SCHEMA.md, API_CONTRACT.md, and project safety rules.
Guarantees:
- Community detection represents structural graph density and correlation, NEVER legal guilt.
- All scores are explainable and grounded in verifiable evidence and multi-source provenance.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CommunityClassification(str, Enum):
    """Investigative classification of a detected community cluster."""
    HIGH_CONNECTIVITY_COMMUNITY = "HIGH_CONNECTIVITY_COMMUNITY"
    CROSS_CASE_COMMUNITY = "CROSS_CASE_COMMUNITY"
    SHARED_DEVICE_CLUSTER = "SHARED_DEVICE_CLUSTER"
    FINANCIAL_LINKED_CLUSTER = "FINANCIAL_LINKED_CLUSTER"
    LOCATION_LINKED_CLUSTER = "LOCATION_LINKED_CLUSTER"
    MIXED_EVIDENCE_COMMUNITY = "MIXED_EVIDENCE_COMMUNITY"
    INCONCLUSIVE_COMMUNITY = "INCONCLUSIVE_COMMUNITY"


class CommunityConfidenceTier(str, Enum):
    """Confidence tier reflecting evidence depth and graph connectivity."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MemberRole(str, Enum):
    """Structural role of an entity within the detected cluster."""
    CORE = "CORE"
    PERIPHERAL = "PERIPHERAL"
    BRIDGE = "BRIDGE"
    INFRASTRUCTURE = "INFRASTRUCTURE"  # Shared phone, vehicle, account, location


class CommunityMember(BaseModel):
    """Individual member entity of a community with its structural role."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    entity_id: str = Field(..., description="Unique entity ID in knowledge graph")
    entity_type: str = Field(..., description="Entity type: PERSON, PHONE, VEHICLE, ACCOUNT, etc.")
    name: Optional[str] = Field(default=None, description="Display name or primary attribute")
    structural_role: MemberRole = Field(default=MemberRole.PERIPHERAL)
    degree: int = Field(default=0, description="Internal connections within the cluster")
    betweenness_score: float = Field(default=0.0, description="Bridge/centrality indicator")


class DetectedCommunity(BaseModel):
    """Structured model representing an algorithmically detected graph community."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    community_id: str = Field(default_factory=lambda: f"COMM_{uuid.uuid4().hex[:8].upper()}")
    classification: CommunityClassification = Field(default=CommunityClassification.MIXED_EVIDENCE_COMMUNITY)
    members: List[CommunityMember] = Field(default_factory=list, description="Detailed list of member entities")
    member_entity_ids: List[str] = Field(default_factory=list, description="List of all entity IDs in community")
    member_count: int = 0
    internal_relationship_count: int = 0
    external_relationship_count: int = 0
    density_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Internal graph edge density [0.0 - 1.0]")
    group_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Investigative cluster suspicion/risk indicator based on measurable graph features")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    confidence_tier: CommunityConfidenceTier = Field(default=CommunityConfidenceTier.HIGH)
    
    # Key Structural Subsets
    central_entity_ids: List[str] = Field(default_factory=list, description="Core central actors/devices")
    bridge_entity_ids: List[str] = Field(default_factory=list, description="Entities bridging to other cases/communities")
    shared_infrastructure_ids: List[str] = Field(default_factory=list, description="Shared phones, vehicles, bank accounts")
    
    # Associations & Provenance
    linked_case_ids: List[str] = Field(default_factory=list, description="Cases associated with members")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="Evidence items corroborating relationships")
    supporting_relationship_ids: List[str] = Field(default_factory=list, description="Internal relationship edges")
    source_provenance_ids: List[str] = Field(default_factory=list, description="Source provenance IDs")
    
    # Actionable Intelligence
    investigative_leads: List[str] = Field(default_factory=list, description="Actionable investigative recommendations")
    limitations: List[str] = Field(default_factory=list, description="Analytical limitations or data gaps")
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    disclaimer: str = Field(
        default="Community detection identifies algorithmic graph clustering and shared infrastructure for investigative prioritization. It does not establish legal guilt or criminal conspiracy.",
        description="Mandatory legal and safety disclaimer"
    )


class CommunityDetectionSummary(BaseModel):
    """Summary response payload for community detection endpoint."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    total_communities: int = 0
    total_clustered_entities: int = 0
    case_id: Optional[str] = None
    communities: List[DetectedCommunity] = Field(default_factory=list)
    disclaimer: str = Field(
        default="CrimeGraph AI community detection identifies graph topological patterns. Human verification is required.",
        description="Safety disclaimer"
    )
