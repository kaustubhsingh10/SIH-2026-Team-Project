"""Automated Tests for Suspicious Pattern Detection Module (Day 20).

Tests SuspiciousPatternEngine, pattern detection algorithms, API endpoints,
filtering, RBAC authorization, audit logging, and safety/non-guilt disclaimers.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.patterns import (
    SuspiciousPatternEngine,
    PatternType,
    PatternSeverity
)
from crimegraph.auth.models import UserRole
from crimegraph.auth.store import UserStore
from crimegraph.auth.security import create_access_token
from crimegraph.audit.logger import AuditLogger
from crimegraph.ai.investigator import AIInvestigator


@pytest.fixture
def graph():
    return load_dataset()


@pytest.fixture
def engine(graph):
    return SuspiciousPatternEngine(graph)


@pytest.fixture
def app_and_client(graph, monkeypatch):
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
    user_store = UserStore()
    audit_logger = AuditLogger()
    app = create_app(graph_instance=graph, user_store=user_store, audit_logger=audit_logger)
    client = TestClient(app)
    return app, client, user_store, audit_logger


@pytest.fixture
def auth_headers():
    token, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# 1. ENGINE UNIT TESTS
# --------------------------------------------------------------------------

def test_engine_detects_patterns(engine):
    patterns = engine.detect_all_patterns()
    assert isinstance(patterns, list)
    assert len(patterns) >= 5

    for p in patterns:
        assert "pattern_id" in p
        assert "pattern_type" in p
        assert "severity" in p
        assert "title" in p
        assert "involved_entities" in p
        assert "involved_cases" in p
        assert "relationships" in p
        assert "supporting_evidence" in p
        assert "explanation" in p
        assert "confidence" in p
        assert "confidence_tier" in p
        assert "investigative_significance" in p
        assert "limitations" in p
        assert "disclaimer" in p
        assert p["confidence"] > 0.0
        assert p["severity"] in [s.value for s in PatternSeverity]
        assert "guilt" not in p["explanation"].lower()
        assert "convict" not in p["explanation"].lower()


def test_detect_shared_device_pattern(engine):
    patterns = engine.detect_all_patterns(pattern_type=PatternType.SHARED_DEVICE_CROSS_CASE.value)
    assert len(patterns) >= 1
    
    phone_pattern = next((p for p in patterns if "PHONE_042" in p["involved_entities"]), None)
    assert phone_pattern is not None
    assert phone_pattern["pattern_type"] == PatternType.SHARED_DEVICE_CROSS_CASE.value
    assert phone_pattern["severity"] == PatternSeverity.HIGH.value
    assert "PERSON_017" in phone_pattern["involved_entities"]
    assert "PERSON_089" in phone_pattern["involved_entities"]
    assert "CASE_101" in phone_pattern["involved_cases"]
    assert "CASE_204" in phone_pattern["involved_cases"]
    assert len(phone_pattern["supporting_evidence"]) > 0


def test_detect_multi_case_coordinator(engine):
    patterns = engine.detect_all_patterns(pattern_type=PatternType.MULTI_CASE_COORDINATOR.value)
    assert len(patterns) >= 1
    
    p17_pattern = next((p for p in patterns if "PERSON_017" in p["involved_entities"]), None)
    assert p17_pattern is not None
    assert p17_pattern["pattern_type"] == PatternType.MULTI_CASE_COORDINATOR.value
    assert len(p17_pattern["involved_cases"]) >= 2
    assert "CASE_101" in p17_pattern["involved_cases"]


def test_detect_cross_case_bridge_paths(engine):
    patterns = engine.detect_all_patterns(pattern_type=PatternType.CROSS_CASE_BRIDGE_PATH.value)
    assert len(patterns) >= 1
    
    bridge = next((p for p in patterns if "CASE_101" in p["involved_cases"] and "CASE_204" in p["involved_cases"]), None)
    assert bridge is not None
    assert "PHONE_042" in bridge["involved_entities"]


def test_detect_high_density_clusters(engine):
    patterns = engine.detect_all_patterns(pattern_type=PatternType.HIGH_DENSITY_CLUSTER.value)
    assert len(patterns) >= 1
    assert any("PERSON_089" in p["involved_entities"] or "PERSON_017" in p["involved_entities"] for p in patterns)


def test_pattern_filtering_by_case(engine):
    patterns_101 = engine.detect_all_patterns(case_id="CASE_101")
    assert len(patterns_101) >= 1
    for p in patterns_101:
        assert "CASE_101" in p["involved_cases"]

    patterns_204 = engine.detect_all_patterns(case_id="CASE_204")
    assert len(patterns_204) >= 1
    for p in patterns_204:
        assert "CASE_204" in p["involved_cases"]


def test_pattern_filtering_by_entity(engine):
    patterns_phone = engine.detect_all_patterns(entity_id="PHONE_042")
    assert len(patterns_phone) >= 1
    for p in patterns_phone:
        assert "PHONE_042" in p["involved_entities"]


def test_pattern_filtering_by_severity(engine):
    high_patterns = engine.detect_all_patterns(min_severity="HIGH")
    for p in high_patterns:
        assert p["severity"] in ["HIGH", "CRITICAL"]


def test_pattern_filtering_by_confidence(engine):
    high_conf = engine.detect_all_patterns(min_confidence=0.95)
    for p in high_conf:
        assert p["confidence"] >= 0.95


def test_no_patterns_found_on_empty_graph():
    empty_graph = KnowledgeGraphStore()
    empty_engine = SuspiciousPatternEngine(empty_graph)
    assert empty_engine.detect_all_patterns() == []


def test_no_patterns_found_on_nonexistent_filters(engine):
    assert engine.detect_all_patterns(case_id="NON_EXISTENT_CASE_999") == []
    assert engine.detect_all_patterns(entity_id="NON_EXISTENT_ENTITY_999") == []


# --------------------------------------------------------------------------
# 2. FASTAPI API ROUTE TESTS
# --------------------------------------------------------------------------

def test_api_get_patterns_unauthenticated(app_and_client):
    _, client, _, _ = app_and_client
    resp = client.get("/api/patterns")
    assert resp.status_code == 401


def test_api_get_patterns_authenticated(app_and_client, auth_headers):
    _, client, _, _ = app_and_client
    resp = client.get("/api/patterns", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "patterns" in data
    assert "total_count" in data
    assert data["total_count"] >= 5
    assert "disclaimer" in data


def test_api_get_patterns_with_query_params(app_and_client, auth_headers):
    _, client, _, _ = app_and_client
    resp = client.get("/api/patterns?case_id=CASE_101&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["patterns"]) <= 2
    for p in data["patterns"]:
        assert "CASE_101" in p["involved_cases"]


def test_api_get_case_patterns(app_and_client, auth_headers):
    _, client, _, _ = app_and_client
    resp = client.get("/api/cases/CASE_101/patterns", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "CASE_101"
    assert len(data["patterns"]) >= 1


def test_api_get_case_patterns_404(app_and_client, auth_headers):
    _, client, _, _ = app_and_client
    resp = client.get("/api/cases/CASE_999/patterns", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_get_entity_patterns(app_and_client, auth_headers):
    _, client, _, _ = app_and_client
    resp = client.get("/api/entities/PERSON_017/patterns", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "PERSON_017"
    assert len(data["patterns"]) >= 1


def test_api_get_entity_patterns_404(app_and_client, auth_headers):
    _, client, _, _ = app_and_client
    resp = client.get("/api/entities/PERSON_999/patterns", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_patterns_audit_logging(app_and_client, auth_headers):
    _, client, _, audit_logger = app_and_client
    client.get("/api/patterns?case_id=CASE_101", headers=auth_headers)
    
    events = [e.model_dump() for e in audit_logger.get_events()]
    pattern_event = next((e for e in events if e.get("action") == "PATTERN_DETECTION_QUERY"), None)
    assert pattern_event is not None
    assert pattern_event["actor_id"] == "analyst"
    assert pattern_event["status"] == "SUCCESS"
    assert pattern_event["details"]["case_id"] == "CASE_101"


# --------------------------------------------------------------------------
# 3. AI INVESTIGATOR & SAFETY TESTS
# --------------------------------------------------------------------------

def test_ai_investigator_pattern_query(graph):
    investigator = AIInvestigator(graph)
    resp = investigator.query("What suspicious patterns exist in the network?")
    assert resp["query_type"] == "SUSPICIOUS_PATTERNS"
    assert "patterns" in resp
    assert len(resp["patterns"]) >= 1
    assert "disclaimer" in resp
    assert "Investigative lead only" in resp["disclaimer"]


def test_safety_and_non_accusatory_language(engine):
    patterns = engine.detect_all_patterns()
    for p in patterns:
        exp = p["explanation"].lower()
        disc = p["disclaimer"].lower()
        assert "guilty" not in exp
        assert "criminal" not in exp
        assert "convict" not in exp
        assert "perpetrator" not in exp
        assert "does not establish legal culpability" in disc
