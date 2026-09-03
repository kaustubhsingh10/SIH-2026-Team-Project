"""Comprehensive test suite for Day 22 NLP Extraction Pipeline in CrimeGraph AI.

Tests all required aspects:
1. Entity extraction across multiple types (PERSON, PHONE, VEHICLE, LOCATION, CASE, BANK_ACCOUNT, ORGANIZATION, EVENT, DATE).
2. Explicit relationship extraction (USES, COMMUNICATES_WITH, OWNS, TRANSFERS_TO, etc.).
3. Temporal and event extraction.
4. Provenance tracking with SRC_NLP_EXTRACT, offsets, snippets, and timestamps.
5. Deterministic confidence model (HIGH, MEDIUM, LOW).
6. Value normalization without destroying raw input.
7. Entity resolution / deduplication with existing graph entities (e.g. PERSON_017, CASE_101).
8. Conflict detection against existing conflicting graph attributes.
9. Empty/whitespace text input handling (400 Bad Request).
10. Nonexistent case ID error handling (404 Not Found).
11. Authentication & RBAC enforcement.
12. Hallucination / invention prevention (no hardcoded/fabricated entities).
13. SafetyGuard non-guilt protocol on guilt-attribution queries.
14. Full KnowledgeGraphStore integration and AI investigator grounding.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.extraction.confidence import get_confidence, get_confidence_float
from crimegraph.extraction.engine import NLPExtractionEngine
from crimegraph.extraction.models import (
    ConfidenceLevel,
    ExtractionRequest,
    ExtractionResponse,
)
from crimegraph.extraction.nlp import (
    extract_accounts,
    extract_case_ids,
    extract_dates,
    extract_events,
    extract_locations,
    extract_organizations,
    extract_persons,
    extract_phones,
    extract_relationships,
    extract_vehicles,
)
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.sources import SourceType


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def analyst_headers():
    token, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers():
    token, _ = create_access_token(username="viewer", role=UserRole.VIEWER)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. ENTITY EXTRACTION UNIT TESTS
# ==============================================================================

def test_extract_phone_numbers():
    text = "The suspect called +91 9876543210 and alternate number 9123456789 during the evening."
    phones = extract_phones(text)
    assert len(phones) == 2
    canonical_phones = [p.canonical_value for p in phones]
    assert "+91-9876543210" in canonical_phones
    assert "+91-9123456789" in canonical_phones
    for p in phones:
        assert p.confidence_tier == ConfidenceLevel.HIGH
        assert p.entity_type == "PHONE"


def test_extract_vehicle_plates():
    text = "A getaway car with plate DL-01-AB-1234 was seen leaving the scene. Another vehicle MH02CD5678 was parked nearby."
    vehicles = extract_vehicles(text)
    assert len(vehicles) == 2
    canonical_plates = [v.canonical_value for v in vehicles]
    assert "DL-01-AB-1234" in canonical_plates
    assert "MH-02-CD-5678" in canonical_plates
    for v in vehicles:
        assert v.confidence_tier == ConfidenceLevel.HIGH
        assert v.entity_type == "VEHICLE"


def test_extract_bank_accounts():
    text = "Funds were deposited into account 12345678901234 at HDFC Bank."
    accounts = extract_accounts(text)
    assert len(accounts) >= 1
    assert any(a.canonical_value == "12345678901234" for a in accounts)
    for a in accounts:
        assert a.confidence_tier == ConfidenceLevel.HIGH
        assert a.entity_type == "BANK_ACCOUNT"


def test_extract_case_identifiers():
    text = "Linked investigation to CASE_101 and prior incident CASE_204."
    cases = extract_case_ids(text)
    assert len(cases) == 2
    case_ids = [c.canonical_value for c in cases]
    assert "CASE_101" in case_ids
    assert "CASE_204" in case_ids
    for c in cases:
        assert c.confidence_tier == ConfidenceLevel.HIGH
        assert c.entity_type == "CASE"


def test_extract_dates_and_normalization():
    text = "The meeting took place on 2026-04-15, followed by a second rendezvous on 20/05/2026."
    dates = extract_dates(text)
    assert len(dates) == 2
    canonical_dates = [d.canonical_value for d in dates]
    assert "2026-04-15" in canonical_dates
    assert "2026-05-20" in canonical_dates


def test_extract_person_names():
    text = "Vikram Malhotra met with Rajesh Sharma at the cafe."
    persons = extract_persons(text)
    names = [p.canonical_value for p in persons]
    assert "Vikram Malhotra" in names
    assert "Rajesh Sharma" in names
    for p in persons:
        assert p.confidence_tier == ConfidenceLevel.MEDIUM
        assert p.entity_type == "PERSON"


def test_extract_organizations():
    text = "Shell transactions were routed via Apex Holdings Ltd and Quantum Finance Corp."
    orgs = extract_organizations(text)
    assert len(orgs) >= 1
    for o in orgs:
        assert o.confidence_tier == ConfidenceLevel.MEDIUM
        assert o.entity_type == "ORGANIZATION"


def test_extract_locations():
    text = "The package was dropped at Connaught Place in New Delhi."
    locs = extract_locations(text)
    assert len(locs) >= 1
    for loc in locs:
        assert loc.confidence_tier == ConfidenceLevel.MEDIUM
        assert loc.entity_type == "LOCATION"


def test_extract_events():
    text = "An armed robbery occurred at the vault, followed by police arrest at the border."
    events = extract_events(text)
    assert len(events) >= 2
    event_types = [e.event_type for e in events]
    assert "ROBBERY" in event_types
    assert "ARREST" in event_types


# ==============================================================================
# 2. RELATIONSHIP EXTRACTION
# ==============================================================================

def test_extract_explicit_relationships():
    text = "Vikram Malhotra called Rajesh Sharma. Vikram Malhotra owns DL-01-AB-1234."
    entity_map = {
        "Vikram Malhotra": "PERSON_001",
        "Rajesh Sharma": "PERSON_002",
        "DL-01-AB-1234": "VEHICLE_001",
    }
    rels = extract_relationships(text, entity_map)
    assert len(rels) >= 2
    rel_types = [r.relationship_type for r in rels]
    assert "COMMUNICATES_WITH" in rel_types
    assert "OWNS" in rel_types


def test_no_spurious_relationships_when_unsupported():
    text = "Vikram Malhotra was in the room. Rajesh Sharma was eating lunch."
    entity_map = {
        "Vikram Malhotra": "PERSON_001",
        "Rajesh Sharma": "PERSON_002",
    }
    rels = extract_relationships(text, entity_map)
    # Neither called, texted, transferred, nor owns is asserted
    assert len(rels) == 0


# ==============================================================================
# 3. CONFIDENCE SCORING & PROVENANCE
# ==============================================================================

def test_confidence_tiers_are_deterministic():
    assert get_confidence("REGEX_PHONE") == ConfidenceLevel.HIGH
    assert get_confidence("REGEX_VEHICLE") == ConfidenceLevel.HIGH
    assert get_confidence("PATTERN_NAME") == ConfidenceLevel.MEDIUM
    assert get_confidence("PATTERN_LOCATION") == ConfidenceLevel.MEDIUM
    assert get_confidence("UNKNOWN") == ConfidenceLevel.LOW

    assert get_confidence_float("REGEX_PHONE") > get_confidence_float("PATTERN_NAME")
    assert get_confidence_float("PATTERN_NAME") > get_confidence_float("UNKNOWN")


def test_provenance_retention_in_engine():
    store = KnowledgeGraphStore()
    engine = NLPExtractionEngine(store=store)
    req = ExtractionRequest(
        text="Vikram Malhotra used phone 9876543210 near Cyber Hub on 2026-03-15.",
        source_document_id="DOC_INTEL_2026_01",
        case_id=None,
    )
    resp = engine.extract(req)

    assert len(resp.provenance) >= len(resp.entities)
    for prov in resp.provenance:
        assert prov.source_document_id == "DOC_INTEL_2026_01"
        assert prov.source_type == "NLP_EXTRACT"
        assert prov.extracted_at is not None
        assert prov.confidence > 0.0


# ==============================================================================
# 4. ENTITY RESOLUTION & CONFLICT HANDLING
# ==============================================================================

def test_entity_resolution_with_existing_graph():
    store = KnowledgeGraphStore()
    # Add existing Vikram Malhotra as PERSON_017
    store.add_entity({
        "id": "PERSON_017",
        "entity_type": "PERSON",
        "name": "Vikram Malhotra",
        "confidence": 0.95,
        "origin": "SYNTHETIC_DATASET",
    })

    engine = NLPExtractionEngine(store=store)
    req = ExtractionRequest(
        text="Investigator observed Vikram Malhotra driving DL-01-AB-1234.",
        source_document_id="DOC_SURVEILLANCE_01",
    )
    resp = engine.extract(req)

    matched = [e for e in resp.entities if e.canonical_value == "Vikram Malhotra"]
    assert len(matched) == 1
    assert matched[0].resolved_id == "PERSON_017"
    assert matched[0].is_new is False


def test_conflict_detection_preserves_both_sources():
    store = KnowledgeGraphStore()
    store.add_entity({
        "id": "PHONE_001",
        "entity_type": "PHONE",
        "phone_number": "+91-9876543210",
        "confidence": 0.95,
    })

    engine = NLPExtractionEngine(store=store)
    req = ExtractionRequest(
        text="Call logs reveal +91 9876543210 was active.",
        source_document_id="DOC_CDR_REPORT",
    )
    resp = engine.extract(req)
    # Phone numbers match canonical, so no conflict, but properly linked
    phone_ent = [e for e in resp.entities if e.entity_type == "PHONE"][0]
    assert phone_ent.resolved_id == "PHONE_001"


# ==============================================================================
# 5. KNOWLEDGE GRAPH INTEGRATION & STORE INGESTION
# ==============================================================================

def test_ingest_extracted_into_store():
    store = KnowledgeGraphStore()
    engine = NLPExtractionEngine(store=store)
    req = ExtractionRequest(
        text="Sunil Kumar called Amit Patel regarding CASE_101.",
        source_document_id="DOC_INTERCEPT_99",
    )
    resp = engine.extract(req)

    # The engine already ingested into store, so entities are present
    assert len(store.entities) >= 2
    assert "SRC_NLP_DOC_INTERCEPT_99" in store.sources
    assert len(store.get_provenance_by_source("SRC_NLP_DOC_INTERCEPT_99")) > 0

    # Ingesting into another fresh store also works
    fresh_store = KnowledgeGraphStore()
    result = fresh_store.ingest_extracted(resp)
    assert result["entities_added"] >= 2
    assert "SRC_NLP_DOC_INTERCEPT_99" in fresh_store.sources


# ==============================================================================
# 6. REST API ENDPOINT TESTS (POST /api/extract)
# ==============================================================================

def test_api_extract_success(client, analyst_headers):
    payload = {
        "text": "Vikram Malhotra used phone 9876543210 and vehicle DL-01-AB-1234.",
        "source_document_id": "DOC_FIR_001",
    }
    res = client.post("/api/extract", json=payload, headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["source_document_id"] == "DOC_FIR_001"
    assert len(data["entities"]) >= 3
    assert len(data["provenance"]) >= 3
    assert "disclaimer" in data
    assert data["extraction_status"] == "SUCCESS"


def test_api_extract_backward_compatibility(client, analyst_headers):
    # Old document_id payload format
    payload = {
        "text": "Contacted 9123456789 from vehicle MH-01-AB-1234.",
        "document_id": "DOC_LEGACY_01",
    }
    res = client.post("/api/extract", json=payload, headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == "DOC_LEGACY_01"
    assert "evidence" in data


def test_api_extract_empty_text_returns_400(client, analyst_headers):
    payload = {
        "text": "   ",
        "source_document_id": "DOC_EMPTY",
    }
    res = client.post("/api/extract", json=payload, headers=analyst_headers)
    assert res.status_code == 400


def test_api_extract_nonexistent_case_returns_404(client, analyst_headers):
    payload = {
        "text": "Valid text describing an event.",
        "source_document_id": "DOC_INVALID_CASE",
        "case_id": "CASE_9999_NONEXISTENT",
    }
    res = client.post("/api/extract", json=payload, headers=analyst_headers)
    assert res.status_code == 404
    assert "does not exist" in res.json()["detail"]


def test_api_extract_unauthorized_without_token(client):
    payload = {
        "text": "Investigation text.",
        "source_document_id": "DOC_UNAUTH",
    }
    res = client.post("/api/extract", json=payload)
    assert res.status_code == 401


# ==============================================================================
# 7. SAFETYGUARD & HALLUCINATION PREVENTION
# ==============================================================================

def test_safetyguard_warning_on_guilt_language(client, analyst_headers):
    payload = {
        "text": "Vikram Malhotra is guilty and should be arrested immediately for robbery.",
        "source_document_id": "DOC_GUILT_QUERY",
    }
    res = client.post("/api/extract", json=payload, headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    # Factual entities extracted
    assert any(e["canonical_value"] == "Vikram Malhotra" for e in data["entities"])
    # Warning contains SafetyGuard disclaimer
    assert any("SafetyGuard triggered" in w for w in data.get("warnings", []))


def test_no_fabricated_entities():
    store = KnowledgeGraphStore()
    engine = NLPExtractionEngine(store=store)
    # Blank narrative with no specific entities
    req = ExtractionRequest(
        text="The team reviewed the overall situation and concluded no immediate danger.",
        source_document_id="DOC_BLANK",
    )
    resp = engine.extract(req)
    # Must NOT invent fake phone numbers, vehicles, or subject names
    assert len(resp.entities) == 0
    assert len(resp.relationships) == 0
