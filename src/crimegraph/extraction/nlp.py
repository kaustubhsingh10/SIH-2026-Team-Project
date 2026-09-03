"""Regex & Pattern-based NLP Extraction for CrimeGraph AI (Day 22).

Design principles:
- Extract ONLY information present in the supplied text.
- Never invent names, phone numbers, accounts, vehicles, locations, or dates.
- Confidence is derived from the determinism of the extraction rule, NOT content.
- No external NLP library dependency — uses stdlib re for portability.
- Extraction is a read-only operation on the text; it never executes it.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from crimegraph.extraction.confidence import get_confidence, get_confidence_float
from crimegraph.extraction.models import (
    ConfidenceLevel,
    ExtractedEntity,
    ExtractedEvent,
    ExtractedRelationship,
)
from crimegraph.sources.normalizer import DataNormalizer


# ---------------------------------------------------------------------------
# Compiled patterns (all case-insensitive where appropriate)
# ---------------------------------------------------------------------------

# Indian mobile numbers: 10-digit starting with 6-9, optional +91 or 91 prefix
_RE_PHONE = re.compile(
    r"(?:\+91[\s\-]?|91[\s\-]?)?(?<!\d)([6-9]\d{9})(?!\d)"
)

# Indian vehicle registration: e.g. DL-01-AB-1234 or DL01AB1234
_RE_VEHICLE = re.compile(
    r"\b([A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{4})\b",
    re.IGNORECASE,
)

# Bank account: 9-18 digit sequences (standalone)
_RE_ACCOUNT = re.compile(r"(?<!\d)(\d{9,18})(?!\d)")

# CrimeGraph canonical IDs
_RE_CASE_ID = re.compile(r"\b(CASE_\d{3,6})\b", re.IGNORECASE)
_RE_PERSON_ID = re.compile(r"\b(PERSON_\d{3,6})\b", re.IGNORECASE)
_RE_PHONE_ID = re.compile(r"\b(PHONE_\d{3,6})\b", re.IGNORECASE)
_RE_VEHICLE_ID = re.compile(r"\b(VEHICLE_\d{3,6})\b", re.IGNORECASE)

# ISO-style dates: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
_RE_DATE_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_RE_DATE_DMY = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b")

# Person names: Two or more capitalised words (Title Case), not ALL-CAPS acronyms
_RE_NAME = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b")

# Organisation keywords
_ORG_SUFFIXES = re.compile(
    r"\b([A-Z][A-Za-z\s]{2,40}(?:Ltd|Limited|Pvt|Inc|Corp|Co|LLP|Bank|Finance|Telecom|Enterprises|Services|Group)\.?)\b"
)

# Location keywords: "at <Place>", "in <Place>", "near <Place>"
_RE_LOCATION = re.compile(
    r"\b(?:at|in|near|from|towards|to)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,3})\b"
)

# Relationship verb patterns: "called", "met", "transferred to", "owns/owned", "used", "contacted"
_RELATIONSHIP_PATTERNS: List[Tuple[str, str, re.Pattern]] = [
    ("COMMUNICATES_WITH", "called",    re.compile(r"(.+?)\s+called\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("COMMUNICATES_WITH", "contacted", re.compile(r"(.+?)\s+contacted\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("COMMUNICATES_WITH", "texted",    re.compile(r"(.+?)\s+texted\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("USES",              "used",      re.compile(r"(.+?)\s+used\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("OWNS",              "owns",      re.compile(r"(.+?)\s+owns?\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("TRANSFERS_TO",      "transferred to", re.compile(r"(.+?)\s+transferred\s+(?:\w+\s+)?to\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("LOCATED_AT",        "located at", re.compile(r"(.+?)\s+(?:is\s+)?located\s+at\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("INVOLVED_IN",       "involved in", re.compile(r"(.+?)\s+(?:is\s+)?involved\s+in\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
    ("MET",               "met",       re.compile(r"(.+?)\s+met\s+(.+?)(?:[,.]|$)", re.IGNORECASE)),
]

# Event keywords
_EVENT_KEYWORDS = re.compile(
    r"\b(robbery|arrest|transfer|meeting|transaction|incident|attack|murder|theft|surveillance|chase|seizure|raid)\b",
    re.IGNORECASE,
)


def _build_entity(
    raw: str,
    entity_type: str,
    canonical: str,
    method: str,
    offset: Tuple[int, int],
    extra: Optional[Dict[str, Any]] = None,
) -> ExtractedEntity:
    tier = get_confidence(method)
    return ExtractedEntity(
        id=f"{entity_type}_EXT_{uuid.uuid4().hex[:6].upper()}",
        entity_type=entity_type,
        raw_value=raw,
        canonical_value=canonical,
        confidence_tier=tier,
        confidence=ConfidenceLevel.to_float(tier),
        extraction_method=method,
        offset_start=offset[0],
        offset_end=offset[1],
        properties=extra or {},
    )


def extract_phones(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()
    for m in _RE_PHONE.finditer(text):
        raw = m.group(0).strip()
        digits = m.group(1)  # 10-digit portion
        if digits in seen:
            continue
        seen.add(digits)
        canonical = DataNormalizer.normalize_phone_number(raw)
        results.append(_build_entity(raw, "PHONE", canonical, "REGEX_PHONE", (m.start(), m.end())))
    
    # Direct canonical phone ID matches (e.g. PHONE_042)
    for m in _RE_PHONE_ID.finditer(text):
        raw = m.group(1).upper()
        if raw in seen:
            continue
        seen.add(raw)
        results.append(_build_entity(raw, "PHONE", raw, "REGEX_PHONE_ID", (m.start(), m.end())))
        
    return results


def extract_vehicles(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()
    for m in _RE_VEHICLE.finditer(text):
        raw = m.group(1).strip()
        canonical = DataNormalizer.normalize_vehicle_registration(raw)
        if canonical in seen:
            continue
        seen.add(canonical)
        results.append(_build_entity(raw, "VEHICLE", canonical, "REGEX_VEHICLE", (m.start(), m.end(1))))
        
    # Direct canonical vehicle ID matches (e.g. VEHICLE_001)
    for m in _RE_VEHICLE_ID.finditer(text):
        raw = m.group(1).upper()
        if raw in seen:
            continue
        seen.add(raw)
        results.append(_build_entity(raw, "VEHICLE", raw, "REGEX_VEHICLE_ID", (m.start(), m.end())))
        
    return results


def extract_accounts(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()
    for m in _RE_ACCOUNT.finditer(text):
        raw = m.group(1)
        canonical = DataNormalizer.normalize_account_number(raw)
        if canonical in seen:
            continue
        seen.add(canonical)
        # Avoid matching dates / years / simple 4-digit numbers
        if len(raw) < 9:
            continue
        results.append(_build_entity(raw, "BANK_ACCOUNT", canonical, "REGEX_ACCOUNT", (m.start(), m.end())))
    return results


def extract_case_ids(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()
    for m in _RE_CASE_ID.finditer(text):
        raw = m.group(1)
        canonical = raw.upper()
        if canonical in seen:
            continue
        seen.add(canonical)
        results.append(_build_entity(raw, "CASE", canonical, "REGEX_CASE_ID", (m.start(), m.end())))
    return results


def extract_dates(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()

    def _add(raw: str, start: int, end: int):
        if raw in seen:
            return
        seen.add(raw)
        # Attempt ISO normalisation
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(raw, fmt)
                canonical = dt.strftime("%Y-%m-%d")
                results.append(_build_entity(raw, "DATE", canonical, "REGEX_DATE", (start, end)))
                return
            except ValueError:
                continue
        results.append(_build_entity(raw, "DATE", raw, "REGEX_DATE", (start, end)))

    for m in _RE_DATE_ISO.finditer(text):
        _add(m.group(1), m.start(), m.end())
    for m in _RE_DATE_DMY.finditer(text):
        _add(m.group(1), m.start(), m.end())
    return results


def extract_persons(text: str) -> List[ExtractedEntity]:
    """Extracts Title Case multi-word names and explicit PERSON_xxx IDs."""
    results = []
    seen: set = set()
    
    # Direct canonical person ID matches (e.g. PERSON_017)
    for m in _RE_PERSON_ID.finditer(text):
        raw = m.group(1).upper()
        if raw in seen:
            continue
        seen.add(raw)
        results.append(_build_entity(raw, "PERSON", raw, "REGEX_PERSON_ID", (m.start(), m.end())))

    # Skip tokens that are abbreviations or entity-type prefixes
    _skip_prefixes = {
        "Case", "Phone", "Vehicle", "Location", "Bank", "Account",
        "Person", "Organization", "Evidence", "Event", "Date",
    }
    for m in _RE_NAME.finditer(text):
        raw = m.group(1).strip()
        if any(raw.startswith(p) for p in _skip_prefixes):
            continue
        canonical = DataNormalizer.normalize_entity_name(raw)
        if canonical in seen or len(canonical.split()) < 2:
            continue
        seen.add(canonical)
        results.append(_build_entity(raw, "PERSON", canonical, "PATTERN_NAME", (m.start(), m.end())))
    return results


def extract_organizations(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()
    for m in _ORG_SUFFIXES.finditer(text):
        raw = m.group(1).strip()
        canonical = DataNormalizer.normalize_entity_name(raw)
        if canonical in seen:
            continue
        seen.add(canonical)
        results.append(_build_entity(raw, "ORGANIZATION", canonical, "PATTERN_ORGANIZATION", (m.start(), m.end())))
    return results


def extract_locations(text: str) -> List[ExtractedEntity]:
    results = []
    seen: set = set()
    for m in _RE_LOCATION.finditer(text):
        raw = m.group(1).strip()
        canonical = DataNormalizer.normalize_entity_name(raw)
        if canonical in seen or len(canonical) < 3:
            continue
        seen.add(canonical)
        results.append(_build_entity(raw, "LOCATION", canonical, "PATTERN_LOCATION", (m.start(1), m.end(1))))
    return results


def extract_events(text: str) -> List[ExtractedEvent]:
    results = []
    for m in _EVENT_KEYWORDS.finditer(text):
        # Extract a short surrounding snippet as description
        snippet_start = max(0, m.start() - 40)
        snippet_end = min(len(text), m.end() + 40)
        snippet = text[snippet_start:snippet_end].strip()
        tier = get_confidence("PATTERN_EVENT")
        results.append(ExtractedEvent(
            event_type=m.group(1).upper(),
            description=snippet,
            confidence_tier=tier,
            confidence=ConfidenceLevel.to_float(tier),
            supporting_text=snippet,
        ))
    return results


def extract_relationships(
    text: str,
    entity_map: Dict[str, str],  # canonical_value / raw_value -> entity_id
) -> List[ExtractedRelationship]:
    """Extracts explicit relationships expressed in text.

    Only creates a relationship when the source text syntactically supports it.
    No inference; no fabrication.
    """
    results = []
    seen: set = set()

    # Split into sentences / clauses
    sentences = re.split(r"[.\n;]", text)

    for sentence in sentences:
        sent = sentence.strip()
        if not sent:
            continue

        for rel_type, verb, pattern in _RELATIONSHIP_PATTERNS:
            for m in pattern.finditer(sent):
                src_raw = m.group(1).strip().rstrip(".,;")
                tgt_raw = m.group(2).strip().rstrip(".,;")
                if not src_raw or not tgt_raw:
                    continue

                # Try direct lookup or substring matching against known entities in this clause
                src_id = entity_map.get(src_raw)
                tgt_id = entity_map.get(tgt_raw)

                if not src_id:
                    for name, eid in entity_map.items():
                        if name.lower() in src_raw.lower() or src_raw.lower() in name.lower():
                            src_id = eid
                            break

                if not tgt_id:
                    for name, eid in entity_map.items():
                        if name.lower() in tgt_raw.lower() or tgt_raw.lower() in name.lower():
                            tgt_id = eid
                            break

                # Only create relationship when BOTH sides reference known or extracted entities
                if not src_id or not tgt_id or src_id == tgt_id:
                    continue

                rel_key = (src_id, tgt_id, rel_type)
                if rel_key in seen:
                    continue
                seen.add(rel_key)

                tier = get_confidence("PATTERN_RELATIONSHIP")
                snippet = sent[:300].strip()
                results.append(ExtractedRelationship(
                    source_entity_id=src_id,
                    target_entity_id=tgt_id,
                    relationship_type=rel_type,
                    confidence_tier=tier,
                    confidence=ConfidenceLevel.to_float(tier),
                    extraction_method="PATTERN_RELATIONSHIP",
                    supporting_text=snippet,
                ))

    return results
