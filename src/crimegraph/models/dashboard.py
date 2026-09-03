"""Data models for Investigation Command Dashboard (Day 31).

Strictly adheres to DATA_SCHEMA.md, API_CONTRACT.md, and Safety Principles.
Guarantees:
- Dashboard metrics represent explainable graph, temporal, and evidence findings.
- Dashboard findings serve as investigative leads only, NEVER legal guilt or intent.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DashboardSummary(BaseModel):
    """Aggregate summary statistics across the CrimeGraph platform."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    total_cases: int = Field(..., description="Total investigation cases in graph")
    active_cases: int = Field(..., description="Active cases undergoing investigation")
    high_priority_cases: int = Field(..., description="High or critical priority cases")
    total_entities: int = Field(..., description="Total tracked entities in graph")
    total_relationships: int = Field(..., description="Total relationship edges in graph")
    total_evidence_count: int = Field(..., description="Total evidence items attached")
    suspicious_patterns_count: int = Field(..., description="Total detected suspicious patterns")
    unresolved_leads_count: int = Field(..., description="Estimated open investigative leads requiring action")


class DashboardCaseOverview(BaseModel):
    """Normalized overview of an investigation case for command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    case_id: str = Field(..., description="Unique case identifier")
    title: str = Field(..., description="Case title or description")
    status: str = Field(default="ACTIVE", description="Case operational status (ACTIVE, OPEN, CLOSED)")
    priority: str = Field(default="HIGH", description="Case priority level (HIGH, MEDIUM, LOW)")
    location: Optional[str] = Field(default="Jurisdiction Alpha", description="Primary geographical location")
    risk_indicator: str = Field(default="HIGH", description="Overall case risk rating based on patterns and connections")
    entity_count: int = Field(..., description="Total entities linked to case")
    relationship_count: int = Field(..., description="Total relationships linked to case")
    evidence_count: int = Field(..., description="Total evidence items attached to case")
    suspicious_pattern_count: int = Field(..., description="Number of suspicious patterns flagged in case")
    last_activity: Optional[str] = Field(default=None, description="ISO timestamp of most recent activity")


class DashboardKeyEntity(BaseModel):
    """Key person or hub entity intelligence for command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    entity_id: str = Field(..., description="Entity unique ID")
    name: str = Field(..., description="Entity display name or title")
    entity_type: str = Field(..., description="Entity category (PERSON, PHONE, VEHICLE, ACCOUNT, etc.)")
    investigation_score: float = Field(..., ge=0.0, le=1.0, description="Influence or network centrality score")
    influence_role: str = Field(default="CORE_HUB", description="Classified network role (CORE_HUB, CROSS_CASE_INFLUENCER, BRIDGE_ENTITY)")
    connection_count: int = Field(..., ge=0, description="Total direct graph connections")
    involved_cases: List[str] = Field(default_factory=list, description="IDs of cases linked to entity")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="Evidence items supporting entity intelligence")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Algorithmic confidence in entity data")


class DashboardPatternItem(BaseModel):
    """Pattern or anomaly item displayed on command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    pattern_id: str = Field(..., description="Unique pattern ID")
    pattern_type: str = Field(..., description="Category of pattern or anomaly")
    title: str = Field(..., description="Pattern title")
    severity: str = Field(..., description="Pattern severity (CRITICAL, HIGH, MEDIUM, LOW)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    involved_entity_ids: List[str] = Field(default_factory=list)
    involved_case_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    explanation: str = Field(...)
    investigative_lead: str = Field(...)


class DashboardCrossCaseItem(BaseModel):
    """Cross-case connection overview for command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    case_a: str = Field(..., description="First case ID")
    case_b: str = Field(..., description="Second case ID")
    connecting_entities: List[str] = Field(default_factory=list, description="Bridge entity IDs linking the two cases")
    path: List[str] = Field(default_factory=list, description="Sequence of entity IDs forming path")
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)


class DashboardPathItem(BaseModel):
    """Link analysis path item for command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    path_id: str = Field(..., description="Path unique ID")
    source_id: str = Field(...)
    target_id: str = Field(...)
    path: List[str] = Field(default_factory=list)
    hop_count: int = Field(...)
    confidence: float = Field(...)
    path_score: float = Field(...)
    explanation: str = Field(...)


class DashboardTimelineEvent(BaseModel):
    """Recent chronological event item for command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    event_id: str = Field(...)
    title: str = Field(...)
    timestamp: str = Field(...)
    event_type: str = Field(...)
    case_id: Optional[str] = Field(default=None)
    entity_ids: List[str] = Field(default_factory=list)
    description: str = Field(...)


class DashboardAIInsight(BaseModel):
    """AI Investigator finding and recommended lead for command dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    topic: str = Field(...)
    summary: str = Field(...)
    confidence: float = Field(...)
    query_type: str = Field(...)
    recommended_lead: str = Field(...)
    evidence_ids: List[str] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    """Unified operational response for Investigation Command Dashboard."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    case_filter: Optional[str] = Field(default=None, description="Case ID filter if dashboard was filtered")
    summary: DashboardSummary = Field(..., description="Platform overview metrics")
    cases: List[DashboardCaseOverview] = Field(default_factory=list, description="Case overviews")
    key_entities: List[DashboardKeyEntity] = Field(default_factory=list, description="Top key-player hub entities")
    suspicious_patterns: List[DashboardPatternItem] = Field(default_factory=list, description="Top detected suspicious patterns")
    cross_case_connections: List[DashboardCrossCaseItem] = Field(default_factory=list, description="Cross-case link connections")
    investigation_paths: List[DashboardPathItem] = Field(default_factory=list, description="Top multi-hop investigation paths")
    recent_events: List[DashboardTimelineEvent] = Field(default_factory=list, description="Chronological timeline events")
    ai_insights: List[DashboardAIInsight] = Field(default_factory=list, description="AI Investigator findings & leads")
    correlations: List[Dict[str, Any]] = Field(default_factory=list, description="Top cross-source intelligence correlations (Day 32)")
    investigative_risk: List[Dict[str, Any]] = Field(default_factory=list, description="Top ranked investigative priority signals (Day 33)")
    command_actions: List[Dict[str, str]] = Field(default_factory=list, description="Supported dashboard navigation action links")
    safety_notice: str = Field(
        default="Dashboard metrics quantify graph topology, temporal events, and evidence confidence for investigative prioritization. They do NOT establish legal guilt or criminal intent.",
        description="Non-culpability legal disclaimer"
    )
