"""Key Player and Influencer Intelligence Data Models for CrimeGraph AI (Day 28).

Provides structured Pydantic schemas for Key Player classification,
sub-metrics breakdown, explainability reasons, and API responses.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class KeyPlayerRole(str, Enum):
    """Classification of key players based on graph topology and influence metrics."""
    CORE_HUB = "CORE_HUB"
    BRIDGE_ENTITY = "BRIDGE_ENTITY"
    CROSS_CASE_INFLUENCER = "CROSS_CASE_INFLUENCER"
    COMMUNITY_INFLUENCER = "COMMUNITY_INFLUENCER"
    HIGH_CONNECTIVITY_ENTITY = "HIGH_CONNECTIVITY_ENTITY"
    INFORMATION_BROKER = "INFORMATION_BROKER"
    EMERGING_KEY_PLAYER = "EMERGING_KEY_PLAYER"


class KeyPlayerSubMetrics(BaseModel):
    """Sub-metric score breakdown powering the composite influence score."""
    model_config = ConfigDict(use_enum_values=True)

    degree_score: float = Field(..., description="Normalized degree centrality (0.0 to 1.0)")
    betweenness_score: float = Field(..., description="Normalized betweenness centrality (0.0 to 1.0)")
    closeness_score: float = Field(..., description="Normalized closeness centrality (0.0 to 1.0)")
    pagerank_score: float = Field(..., description="Normalized PageRank influence (0.0 to 1.0)")
    cross_case_score: float = Field(..., description="Cross-case reach score (0.0 to 1.0)")
    community_reach_score: float = Field(..., description="Cross-community reach score (0.0 to 1.0)")
    bridge_score: float = Field(..., description="Structural bridge importance score (0.0 to 1.0)")
    direct_connections: int = Field(..., description="Raw count of 1-hop connected neighbors")
    raw_betweenness: float = Field(..., description="Raw Brandes betweenness centrality score")
    case_count: int = Field(..., description="Count of distinct connected cases")
    community_reach_count: int = Field(..., description="Count of distinct communities reached")
    evidence_count: int = Field(..., description="Count of supporting evidentiary items")
    average_edge_confidence: float = Field(..., description="Average confidence of incident relationships")


class KeyPlayerItem(BaseModel):
    """Comprehensive explainable key player intelligence record."""
    model_config = ConfigDict(use_enum_values=True)

    rank: int = Field(..., description="1-based influence rank")
    entity_id: str = Field(..., description="Unique entity ID (e.g. PERSON_017)")
    entity_name: str = Field(..., description="Entity display name or primary label")
    entity_type: str = Field(..., description="Entity category (e.g. PERSON, PHONE, VEHICLE)")
    score: float = Field(..., description="Composite influence score (0.0 to 1.0)")
    influence_role: KeyPlayerRole = Field(..., description="Key player analytical classification")
    metrics: KeyPlayerSubMetrics = Field(..., description="Sub-metrics breakdown")
    connected_case_ids: List[str] = Field(default_factory=list, description="IDs of cases connected to this entity")
    connected_entity_count: int = Field(..., description="Count of direct neighbor entities")
    bridge_count: int = Field(default=0, description="Estimated shortest paths traversing this entity node")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting evidence files/items")
    provenance: str = Field(default="DATASET", description="Data origin (DATASET, MANUAL, NLP_EXTRACT)")
    explanation: str = Field(..., description="Human-readable investigative justification")
    reasons: List[str] = Field(default_factory=list, description="Key investigative factors")
    confidence: float = Field(..., description="Overall metrics confidence level (0.0 to 1.0)")


class KeyPlayerResponse(BaseModel):
    """API response container for key player intelligence endpoints."""
    model_config = ConfigDict(use_enum_values=True)

    scope: str = Field(default="GLOBAL", description="Analysis scope: GLOBAL or CASE_ID")
    case_id: Optional[str] = Field(default=None, description="Scope case ID if case-filtered")
    filter_role: Optional[str] = Field(default=None, description="Applied role filter")
    filter_entity_type: Optional[str] = Field(default=None, description="Applied entity type filter")
    total_entities_analyzed: int = Field(..., description="Total nodes in graph/subgraph scope")
    key_players_count: int = Field(..., description="Count of returned key player records")
    key_players: List[KeyPlayerItem] = Field(..., description="Ranked key player records")
    safety_notice: str = Field(
        default="Network influence metrics quantify graph topology, structural connectivity, and information flow. They do NOT establish legal guilt or criminal culpability.",
        description="Mandatory non-culpability safety disclaimer"
    )
