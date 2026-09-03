"""Structured Investigation Report Models for CrimeGraph AI (Day 24).

Adheres to PROJECT_SPEC.md, DATA_SCHEMA.md, API_CONTRACT.md, and Safety Principles.
Backward compatible with InvestigationResponse and POST /api/reports.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ReportExportFormat(str, Enum):
    """Supported report export formats."""
    JSON = "JSON"
    PDF = "PDF"
    HTML = "HTML"
    MARKDOWN = "MARKDOWN"


class InvestigationReport(BaseModel):
    """Comprehensive, evidence-grounded investigation report."""
    model_config = ConfigDict(extra="allow", use_enum_values=True)

    report_id: str = Field(default_factory=lambda: f"REPORT_{uuid.uuid4().hex[:8].upper()}")
    case_ids: List[str] = Field(default_factory=list, description="Primary and related case IDs")
    case_id: Optional[str] = Field(default=None, description="Primary case ID for backward compatibility")
    title: str = Field(..., description="Report title")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generated_by: str = Field(default="SYSTEM", description="Investigator username or system actor")
    generation_method: str = Field(default="MULTI_SOURCE_GRAPH_SYNTHESIS", description="Method used to generate report")
    
    # Executive & Investigation Context
    investigation_question: Optional[str] = Field(default=None, description="Specific query or objective")
    executive_summary: str = Field(..., description="High-level factual executive summary")
    
    # Grounded Graph Findings
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Structured entity records with details")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="Structured relationship edges with confidence")
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list, description="Chronological timeline events")
    suspicious_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="Detected patterns (shared devices, clusters)")
    network_intelligence: Dict[str, Any] = Field(default_factory=dict, description="Influencers, bridges, centrality scores")
    cross_case_connections: List[Dict[str, Any]] = Field(default_factory=list, description="Discovered cross-case bridge paths")
    
    # Evidence & Provenance Lineage
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Attached evidence items with source text")
    evidence_ids: List[str] = Field(default_factory=list, description="List of evidence IDs referenced")
    source_provenance: List[Dict[str, Any]] = Field(default_factory=list, description="Source records and origin breakdown")
    
    # Confidence & Lead Generation
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    confidence_tier: str = Field(default="HIGH", description="HIGH, MEDIUM, LOW")
    investigative_leads: List[str] = Field(default_factory=list, description="Recommended next steps for human investigators")
    limitations: List[str] = Field(default_factory=list, description="Data gaps, unverified leads, or uncertainties")
    
    # Safety & Legal Protections
    is_safe: bool = Field(default=True)
    disclaimer: str = Field(
        default="CrimeGraph AI reports are algorithmic investigative intelligence summaries and do not establish legal guilt or criminal liability."
    )
    
    # Markdown Content representation
    content: Optional[str] = Field(default=None, description="Rendered markdown report content for backward compatibility")
    status: str = Field(default="generated", description="Report status: generated, exported, archived")


class ReportRequest(BaseModel):
    """Request payload for generating an investigation report."""
    case_id: Optional[str] = Field(default=None, description="Primary case ID")
    case_ids: Optional[List[str]] = Field(default=None, description="Multiple case IDs for cross-case report")
    question: Optional[str] = Field(default=None, description="Targeted natural language investigation question")
    include_timeline: bool = Field(default=True, description="Whether to include chronological timeline")
    include_patterns: bool = Field(default=True, description="Whether to include suspicious pattern detection")
    include_network_intelligence: bool = Field(default=True, description="Whether to include centrality and influencer rankings")
    include_evidence: bool = Field(default=True, description="Whether to include evidence catalog citations")
