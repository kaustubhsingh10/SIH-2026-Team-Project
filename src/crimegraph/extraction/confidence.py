"""Deterministic Confidence Scoring for NLP Extraction (Day 22).

Maps extraction technique name -> ConfidenceLevel tier.
Confidence is NEVER based on how "guilty-sounding" the content is.
"""

from crimegraph.extraction.models import ConfidenceLevel


# Deterministic mapping: technique -> tier
_METHOD_TIERS: dict = {
    # Strict regular expression match (unambiguous format)
    "REGEX_PHONE": ConfidenceLevel.HIGH,
    "REGEX_VEHICLE": ConfidenceLevel.HIGH,
    "REGEX_ACCOUNT": ConfidenceLevel.HIGH,
    "REGEX_CASE_ID": ConfidenceLevel.HIGH,
    "REGEX_DATE": ConfidenceLevel.HIGH,
    # Structural pattern (title-case name, keyword-anchored relationship)
    "PATTERN_NAME": ConfidenceLevel.MEDIUM,
    "PATTERN_LOCATION": ConfidenceLevel.MEDIUM,
    "PATTERN_ORGANIZATION": ConfidenceLevel.MEDIUM,
    "PATTERN_EVENT": ConfidenceLevel.MEDIUM,
    "PATTERN_RELATIONSHIP": ConfidenceLevel.MEDIUM,
    "PATTERN_EVIDENCE_REF": ConfidenceLevel.MEDIUM,
    # Heuristic / relaxed fallback
    "HEURISTIC_KEYWORD": ConfidenceLevel.LOW,
    "HEURISTIC_PROXIMITY": ConfidenceLevel.LOW,
    # Default when method is unspecified
    "UNKNOWN": ConfidenceLevel.LOW,
}


def get_confidence(method: str) -> ConfidenceLevel:
    """Returns the deterministic ConfidenceLevel for a given extraction method.

    Never returns HIGH for heuristic methods or LOW for strict regex.
    The mapping is static and cannot be influenced by text content.
    """
    return _METHOD_TIERS.get(method, ConfidenceLevel.LOW)


def get_confidence_float(method: str) -> float:
    """Returns a numeric float for a given extraction method (for ProvenanceRecord)."""
    return ConfidenceLevel.to_float(get_confidence(method))
