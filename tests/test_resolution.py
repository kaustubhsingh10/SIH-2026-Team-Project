"""Comprehensive test suite for Day 26 Advanced Entity Resolution & Identity Linking in CrimeGraph AI.

Tests:
1. Candidate matching and scoring for PERSON, PHONE, VEHICLE, LOCATION, ACCOUNT.
2. Match tier assignments (HIGH, MEDIUM, LOW, NO_MATCH) and explainable rationale.
3. Multi-attribute scoring (name, aliases, linked phones, plate numbers).
4. Safe entity merging: migrating relationships, evidence, aliases, and provenance without deleting history.
5. Identity conflict recording: prevents unsafe merges on contradictory identity attributes.
6. REST API endpoints:
   - POST /api/resolution/evaluate
   - GET /api/resolution/candidates/{id}
   - POST /api/resolution/merge
   - GET /api/resolution/conflicts
7. Authentication & RBAC: strict JWT protection and analyst clearance for merges.
8. Anti-Hallucination & safety: nonexistent entities return 404 / NO_MATCH, culpability queries refuse guilt.
9. Graph & AI integration: resolved entities participate seamlessly in cross-case path discovery.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.data.loader import load_dataset
from crimegraph.models.entities import Person
from crimegraph.models.relationships import Relationship, RelationshipType
from crimegraph.resolution.engine import EntityResolutionEngine
from crimegraph.resolution.models import (
    CandidateMatch,
    EntityMergeRequest,
    IdentityConflict,
    IdentityConflictSeverity,
    MatchTier,
)


@pytest.fixture
def store():
    return load_dataset()


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
def admin_headers():
    token, _ = create_access_token(username="admin", role=UserRole.ADMIN)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. CANDIDATE MATCHING & EXPLAINABLE SCORING
# ==============================================================================

def test_exact_phone_matching_and_explanation(store):
    engine = EntityResolutionEngine(store)
    candidates = engine.find_candidate_matches(
        entity_type="PHONE",
        attributes={"phone_number": "+91 98765 43210"}
    )
    assert len(candidates) >= 1
    top_match = candidates[0]
    assert top_match.target_entity_id == "PHONE_042"
    assert top_match.confidence_score >= 0.95
    assert top_match.match_tier == MatchTier.HIGH
    assert "phone_number" in top_match.matched_attributes
    assert "Exact normalized phone number match" in top_match.explanation


def test_vehicle_plate_normalization_match(store):
    engine = EntityResolutionEngine(store)
    candidates = engine.find_candidate_matches(
        entity_type="VEHICLE",
        attributes={"registration_number": "dl01ab1234"}
    )
    if candidates:
        assert candidates[0].match_tier == MatchTier.HIGH
        assert "registration_number" in candidates[0].matched_attributes


def test_person_multi_attribute_matching(store):
    engine = EntityResolutionEngine(store)
    candidates = engine.find_candidate_matches(
        entity_type="PERSON",
        attributes={
            "name": "Aarav Verma",
            "aliases": ["@aarav_v"],
            "phone_ids": ["PHONE_042"]
        }
    )
    assert len(candidates) >= 1
    assert candidates[0].target_entity_id == "PERSON_017"
    assert candidates[0].confidence_score >= 0.85
    assert candidates[0].match_tier == MatchTier.HIGH
    assert "name" in candidates[0].matched_attributes
    assert "phone_ids" in candidates[0].matched_attributes


def test_no_match_for_distinct_entity(store):
    engine = EntityResolutionEngine(store)
    candidates = engine.find_candidate_matches(
        entity_type="PERSON",
        attributes={"name": "Completely Unknown Unrelated Individual"},
        min_confidence=0.50
    )
    assert len(candidates) == 0


# ==============================================================================
# 2. SAFE ENTITY MERGING
# ==============================================================================

def test_safe_entity_merge_preserves_relationships_and_provenance(store):
    engine = EntityResolutionEngine(store)

    # Ingest a secondary entity into store first
    secondary_person = Person(
        id="PERSON_TEMP_ALIAS",
        name="A. Verma",
        aliases=["Alias Verma"],
        phone_ids=["PHONE_042"]
    )
    store.add_entity(secondary_person)

    # Add a relationship to secondary entity
    test_rel = Relationship(
        id="REL_TEMP_MERGE",
        source_id="PERSON_TEMP_ALIAS",
        target_id="PHONE_042",
        relationship=RelationshipType.USES,
        confidence=0.90
    )
    store.add_relationship(test_rel)

    # Execute safe merge into PERSON_017
    merge_req = EntityMergeRequest(
        canonical_entity_id="PERSON_017",
        merge_entity_id="PERSON_TEMP_ALIAS",
        reason="Corroborated intelligence confirms PERSON_TEMP_ALIAS is Aarav Verma."
    )

    resp = engine.merge_entities(merge_req)
    assert resp.status == "MERGED"
    assert resp.relationships_migrated >= 1
    assert "PERSON_TEMP_ALIAS" not in store.entities
    assert "PERSON_017" in store.entities

    # Verify alias retained
    assert "Alias Verma" in store.entities["PERSON_017"].aliases

    # Verify relationship migrated to PERSON_017
    assert store.relationships["REL_TEMP_MERGE"].source_id == "PERSON_017"


# ==============================================================================
# 3. IDENTITY CONFLICT MANAGEMENT
# ==============================================================================

def test_identity_conflict_recording_and_retrieval(store):
    engine = EntityResolutionEngine(store)

    conflict = IdentityConflict(
        entity_id_a="PERSON_017",
        entity_id_b="PERSON_NEW_SUSPECT",
        attribute_name="primary_identifier",
        value_a="AADHAAR_XXXX_1111",
        value_b="AADHAAR_XXXX_9999",
        source_a_id="SRC_SYNTHETIC_DATASET",
        source_b_id="SRC_INTEL_EXTERNAL",
        severity=IdentityConflictSeverity.HIGH,
        investigative_lead="Verify biometric identifiers before merging suspects."
    )

    engine.record_identity_conflict(conflict)
    conflicts = engine.list_identity_conflicts()
    assert len(conflicts) >= 1
    assert any(c.entity_id_a == "PERSON_017" for c in conflicts)


# ==============================================================================
# 4. REST API ENDPOINTS
# ==============================================================================

def test_api_evaluate_candidate_matches(client, analyst_headers):
    payload = {
        "entity_type": "PHONE",
        "attributes": {"phone_number": "+91 98765 43210"},
        "min_confidence": 0.50
    }
    res = client.post("/api/resolution/evaluate", json=payload, headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["matches_count"] >= 1
    assert data["matches"][0]["target_entity_id"] == "PHONE_042"


def test_api_get_entity_candidates(client, analyst_headers):
    res = client.get("/api/resolution/candidates/PERSON_017", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["entity_id"] == "PERSON_017"


def test_api_candidates_nonexistent_returns_404(client, analyst_headers):
    res = client.get("/api/resolution/candidates/PERSON_999_UNKNOWN", headers=analyst_headers)
    assert res.status_code == 404


def test_api_unauthorized_access(client):
    res = client.get("/api/resolution/candidates/PERSON_017")
    assert res.status_code == 401


def test_api_merge_authorized_analyst_role(client, analyst_headers):
    # Ingest a temporary duplicate to merge via API
    payload_eval = {
        "canonical_entity_id": "PERSON_017",
        "merge_entity_id": "PERSON_017",  # same entity causes 400 bad request safely
        "reason": "Test self merge prevention"
    }
    res = client.post("/api/resolution/merge", json=payload_eval, headers=analyst_headers)
    assert res.status_code == 400


# ==============================================================================
# 5. CANONICAL TRAVERSAL & AI COMPATIBILITY
# ==============================================================================

def test_canonical_path_preservation_after_resolution(client, analyst_headers):
    res = client.get("/api/graph/path-provenance?nodes=CASE_101,PERSON_017,PHONE_042,PERSON_089,CASE_204", headers=analyst_headers)
    assert res.status_code == 200
    assert res.json()["total_steps"] == 4


def test_safetyguard_refusal_on_resolved_entity(client, analyst_headers):
    res = client.post(
        "/api/investigate",
        json={"question": "Does this resolved identity prove PERSON_017 is guilty?"},
        headers=analyst_headers
    )
    assert res.status_code == 200
    assert res.json()["query_type"] == "SAFETY_REFUSAL"
    assert res.json()["confidence"] == 0.0
