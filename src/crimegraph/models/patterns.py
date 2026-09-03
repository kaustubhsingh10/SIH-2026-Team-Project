"""Data models for Advanced AI Pattern & Anomaly Intelligence (Day 30).

Strictly adheres to DATA_SCHEMA.md and API_CONTRACT.md.
Guarantees:
- Anomaly scores represent explainable, deterministic graph and behavioral metrics.
- Pattern outputs provide investigative leads only, NEVER legal guilt or intent.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class PatternType(str, Enum):
    """Supported suspicious relationship & anomaly pattern categories."""
    # Day 30 Core Pattern Types
    HIGH_CONNECTIVITY_HUB = "HIGH_CONNECTIVITY_HUB"
    UNUSUAL_DEGREE_SPIKE = "UNUSUAL_DEGREE_SPIKE"
    CROSS_CASE_BRIDGE = "CROSS_CASE_BRIDGE"
    RAPID_ENTITY_EXPANSION = "RAPID_ENTITY_EXPANSION"
    REPEATED_CONTACT_PATTERN = "REPEATED_CONTACT_PATTERN"
    TEMPORAL_CLUSTER = "TEMPORAL_CLUSTER"
    SUSPICIOUS_SEQUENCE = "SUSPICIOUS_SEQUENCE"
    MULTI_SOURCE_CORROBORATION = "MULTI_SOURCE_CORROBORATION"
    ENTITY_ACTIVITY_ANOMALY = "ENTITY_ACTIVITY_ANOMALY"
    UNUSUAL_PATH_PATTERN = "UNUSUAL_PATH_PATTERN"

    # Legacy Backward-Compatible Categories
    SHARED_DEVICE_CROSS_CASE = "SHARED_DEVICE_CROSS_CASE"
    MULTI_CASE_COORDINATOR = "MULTI_CASE_COORDINATOR"
    CROSS_CASE_BRIDGE_PATH = "CROSS_CASE_BRIDGE_PATH"
    HIGH_DENSITY_CLUSTER = "HIGH_DENSITY_CLUSTER"
    MULTI_LOCATION_MOVEMENT = "MULTI_LOCATION_MOVEMENT"
    SHARED_FINANCIAL_ACCOUNT = "SHARED_FINANCIAL_ACCOUNT"


class PatternSeverity(str, Enum):
    """Categorical severity rating for detected suspicious patterns."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PatternAnomalyItem(BaseModel):
    """Detailed suspicious pattern or anomaly finding."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    pattern_id: str = Field(default_factory=lambda: f"PAT_{uuid.uuid4().hex[:8].upper()}")
    pattern_type: str = Field(..., description="Category of detected pattern or anomaly")
    title: str = Field(..., description="Short descriptive title of the pattern finding")
    severity: PatternSeverity = Field(default=PatternSeverity.MEDIUM)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Algorithmic confidence in pattern accuracy")
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Explainable composite anomaly score")
    involved_entity_ids: List[str] = Field(default_factory=list, description="IDs of graph entities participating in pattern")
    involved_case_ids: List[str] = Field(default_factory=list, description="IDs of cases linked to this pattern")
    related_event_ids: List[str] = Field(default_factory=list, description="IDs of timeline events linked to this pattern")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs")
    explanation: str = Field(..., description="Machine-readable rationale describing why pattern was flagged")
    investigative_lead: str = Field(..., description="Actionable recommended lead for investigators")
    provenance_sources: List[str] = Field(default_factory=list, description="Data sources corroborating pattern")
    scoring_factors: Dict[str, float] = Field(default_factory=dict, description="Factor breakdown of anomaly score")
    disclaimer: str = Field(
        default="Pattern & anomaly metrics identify topological and temporal graph signals for investigative prioritization. They do NOT establish legal guilt or criminal intent.",
        description="SafetyGuard non-culpability legal disclaimer"
    )


class PatternDetectionRequest(BaseModel):
    """Payload for executing a pattern detection sweep."""
    case_id: Optional[str] = Field(default=None, description="Optional case ID filter")
    entity_id: Optional[str] = Field(default=None, description="Optional entity ID filter")
    pattern_type: Optional[str] = Field(default=None, description="Optional pattern type filter")
    min_score: float = Field(default=0.30, ge=0.0, le=1.0, description="Minimum anomaly score threshold")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum pattern items to return")


class PatternQueryResponse(BaseModel):
    """Structured response for suspicious pattern queries."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    total_patterns: int = Field(..., description="Total pattern items found")
    patterns: List[PatternAnomalyItem] = Field(default_factory=list, description="List of detected pattern findings")
    safety_notice: str = Field(
        default="Pattern & anomaly metrics identify topological and temporal graph signals for investigative prioritization. They do NOT establish legal guilt or criminal intent.",
        description="Non-culpability legal disclaimer"
    )
