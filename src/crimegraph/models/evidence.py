"""Evidence model for CrimeGraph AI.

Strictly adheres to DATA_SCHEMA.md Section 3 (Evidence Model) and Section 4 (Confidence).
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    """Evidence model linking extracted entities and relationships to their sources.
    
    Fields defined in DATA_SCHEMA.md:
    - evidence_id: Unique evidence identifier (e.g. EVID_001)
    - source_document_id: Identifier or filename of source doc (e.g. DOC_001, Case101_Report.pdf)
    - source_text: Exact or extracted snippet of source text
    - page_number: Page number in source document (optional)
    - timestamp: ISO 8601 timestamp string
    - extraction_method: Extraction method (e.g. AI_NER, MANUAL, CALL_RECORD, OCR)
    - confidence: Confidence score between 0.0 and 1.0
    """
    evidence_id: str = Field(..., description="Unique evidence identifier")
    source_document_id: str = Field(..., description="Identifier or filename of source document")
    source_text: str = Field(..., description="Source text or extract")
    page_number: Optional[int] = Field(default=None, description="Page number in document")
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 timestamp")
    extraction_method: Optional[str] = Field(default=None, description="Extraction method")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)

    @property
    def confidence_tier(self) -> str:
        """Returns High (0.90-1.00), Medium (0.70-0.89), or Low (<0.70) per DATA_SCHEMA.md."""
        if self.confidence >= 0.90:
            return "High"
        elif self.confidence >= 0.70:
            return "Medium"
        else:
            return "Low"
