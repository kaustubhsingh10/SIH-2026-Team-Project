"""Data models for Day 33 — ML / Data Mining + Investigative Risk Scoring.

Defines Pydantic models for explainable risk features, contributing signal weights,
entity risk scores, case-level risk prioritization, and API response structures.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    """Categorical risk prioritization level."""
    LOW = "LOW"            # Score 0 - 29: Baseline graph activity
    MODERATE = "MODERATE"   # Score 30 - 59: Notable network connections or patterns
    HIGH = "HIGH"          # Score 60 - 84: High-density anomalies or cross-case links
    CRITICAL = "CRITICAL"  # Score 85 - 100: Critical multi-source correlation & anomaly alignment


class RiskSignal(BaseModel):
    """Individual contributing signal factor towards total risk score."""
    model_config = ConfigDict(extra="ignore")

    signal_type: str = Field(..., description="Category of signal (e.g. CROSS_CASE_HUB, ANOMALY_CLUSTER, MULTI_SOURCE_CORRELATION)")
    description: str = Field(..., description="Human-readable explanation of why this signal contributes to risk")
    weight: float = Field(..., ge=0.0, le=1.0, description="Normalized weight factor of signal")
    score_contribution: float = Field(..., ge=0.0, le=100.0, description="Numerical points added to total risk score")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence items linked to signal")


class EntityRiskFeatureVector(BaseModel):
    """Data-mining feature vector extracted from knowledge graph topology & analytics engines."""
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    entity_type: str
    degree: int = 0
    weighted_degree: float = 0.0
    case_count: int = 0
    community_count: int = 0
    cross_case_count: int = 0
    centrality_score: float = 0.0
    anomaly_score: float = 0.0
    pattern_count: int = 0
    correlation_score: float = 0.0
    cross_source_count: int = 0
    evidence_count: int = 0


class EntityRiskResponse(BaseModel):
    """Explainable risk score and priority signal breakdown for a specific entity."""
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    entity_name: str
    entity_type: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Normalized investigative priority score (0-100)")
    risk_level: RiskLevel
    confidence: float = Field(0.95, ge=0.0, le=1.0, description="Confidence in underlying data quality and feature completeness")
    features: EntityRiskFeatureVector
    signals: List[RiskSignal] = Field(default_factory=list)
    involved_cases: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    source_records: List[str] = Field(default_factory=list)
    explanation: str
    investigative_lead: str
    disclaimer: str = (
        "Investigative priority score quantifies graph topology, pattern density, and cross-source alignment "
        "for investigative resource allocation. It does NOT indicate legal guilt or criminal probability."
    )


class CaseRiskResponse(BaseModel):
    """Case-level investigation risk prioritization and complexity assessment."""
    model_config = ConfigDict(extra="ignore")

    case_id: str
    case_title: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Aggregated case investigation priority score (0-100)")
    risk_level: RiskLevel
    confidence: float = 0.95
    total_entities: int = 0
    high_risk_entity_count: int = 0
    cross_case_link_count: int = 0
    pattern_count: int = 0
    correlation_count: int = 0
    top_risk_entities: List[Dict[str, Any]] = Field(default_factory=list)
    signals: List[RiskSignal] = Field(default_factory=list)
    explanation: str
    investigative_lead: str
    disclaimer: str = (
        "Investigative priority score quantifies graph topology, pattern density, and cross-source alignment "
        "for investigative resource allocation. It does NOT indicate legal guilt or criminal probability."
    )


class RiskPriorityItem(BaseModel):
    """Item in ranked investigation priority queue."""
    model_config = ConfigDict(extra="ignore")

    rank: int
    entity_id: str
    entity_name: str
    entity_type: str
    risk_score: float
    risk_level: RiskLevel
    primary_signal_type: str
    involved_cases: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    explanation: str
    investigative_lead: str


class RiskPriorityQueryResponse(BaseModel):
    """Response wrapper for ranked investigation priority queries."""
    model_config = ConfigDict(extra="ignore")

    case_filter: Optional[str] = None
    min_score: float = 0.0
    total_count: int
    priorities: List[RiskPriorityItem] = Field(default_factory=list)
    disclaimer: str = (
        "Investigative priority score quantifies graph topology, pattern density, and cross-source alignment "
        "for investigative resource allocation. It does NOT indicate legal guilt or criminal probability."
    )


class RiskAnalyzeRequest(BaseModel):
    """Custom request payload for multi-entity risk scoring analysis."""
    model_config = ConfigDict(extra="ignore")

    entity_ids: Optional[List[str]] = None
    case_id: Optional[str] = None
    min_score: float = 0.0
    limit: int = 50
