"""Data models for Advanced Link Analysis & Path Discovery (Day 29).

Strictly adheres to DATA_SCHEMA.md and API_CONTRACT.md.
Guarantees:
- Path scores represent graph-derived topological metrics and evidence confidence.
- Path analysis provides investigative leads only, NEVER legal guilt or intent.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TemporalAlignment(str, Enum):
    """Chronological sequence indicator for path relationship timestamps."""
    CHRONOLOGICAL = "CHRONOLOGICAL"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    UNDATED = "UNDATED"


class PathStep(BaseModel):
    """Structured step in a discovered relationship path."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    from_entity_id: str = Field(..., description="Source entity ID for this step")
    to_entity_id: str = Field(..., description="Target entity ID for this step")
    relationship_type: str = Field(..., description="Relationship label (e.g., USES, CONTACTED, INVOLVED_IN)")
    relationship_id: str = Field(..., description="Unique relationship ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Edge confidence score")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp if recorded")
    provenance: str = Field(default="DATASET", description="Origin source (DATASET, MANUAL, NLP_EXTRACT)")


class PathAnalysisItem(BaseModel):
    """Detailed candidate path item discovered between two entities or cases."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    path_id: str = Field(default_factory=lambda: f"PATH_{uuid.uuid4().hex[:8].upper()}")
    source_id: str = Field(..., description="Origin node ID")
    target_id: str = Field(..., description="Destination node ID")
    path: List[str] = Field(..., description="Sequence of entity IDs forming the path")
    hop_count: int = Field(..., ge=0, description="Total relationship hops")
    path_score: float = Field(..., ge=0.0, le=1.0, description="Composite explainable path score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Minimum edge confidence along chain")
    average_edge_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence across edges")
    evidence_ids: List[str] = Field(default_factory=list, description="All supporting evidence IDs")
    provenance_sources: List[str] = Field(default_factory=list, description="Unique data provenance sources")
    steps: List[PathStep] = Field(default_factory=list, description="Step-by-step relationship details")
    shared_entities: List[str] = Field(default_factory=list, description="Intermediate pivot entities")
    temporal_alignment: TemporalAlignment = Field(default=TemporalAlignment.UNDATED)
    explanation: str = Field(..., description="Machine-readable rationale explaining the path discovery")
    scoring_factors: Dict[str, float] = Field(default_factory=dict, description="Breakdown of path score components")


class PathAnalysisRequest(BaseModel):
    """Payload for path discovery request."""
    source_id: str = Field(..., description="Source entity or case ID")
    target_id: str = Field(..., description="Target entity or case ID")
    max_depth: int = Field(default=5, ge=1, le=10, description="Maximum hop depth limit")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of candidate paths to return")
    include_temporal: bool = Field(default=True, description="Whether to evaluate temporal chronological alignment")


class PathAnalysisResponse(BaseModel):
    """Structured response for link analysis and path discovery."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    max_depth: int = Field(..., description="Hop depth limit evaluated")
    total_paths_found: int = Field(..., description="Number of candidate paths discovered")
    paths: List[PathAnalysisItem] = Field(default_factory=list, description="Ranked list of candidate paths")
    safety_notice: str = Field(
        default="Path analysis quantifies topological connectivity and relationship evidence. It does NOT establish legal guilt or criminal intent.",
        description="Non-culpability legal disclaimer"
    )
