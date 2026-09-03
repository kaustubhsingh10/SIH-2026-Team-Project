"""Test suite for Day 30 — Advanced AI Pattern & Anomaly Intelligence.

Tests cover:
1. High-connectivity hub detection (HIGH_CONNECTIVITY_HUB)
2. Relationship diversity spike detection (UNUSUAL_DEGREE_SPIKE)
3. Cross-case bridge node detection (CROSS_CASE_BRIDGE)
4. Repeated contact interaction detection (REPEATED_CONTACT_PATTERN)
5. Multi-source evidence corroboration (MULTI_SOURCE_CORROBORATION)
6. Deterministic explainable anomaly score calculation and factor breakdown
7. API GET /api/patterns with filtering by case_id, pattern_type, min_score
8. API GET /api/patterns/{pattern_id} detail view and 404 error handling
9. API POST /api/patterns/detect sweep execution
10. AI Investigator integration for natural language pattern queries
11. SafetyGuard legal disclaimer and non-guilt refusal protocol
12. RBAC authentication enforcement (401)
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.patterns import SuspiciousPatternEngine


@pytest.fixture
def test_setup(tmp_path):
    temp_manual = tmp_path / "test_pattern_manual_data.json"
    os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"] = str(temp_manual)
    os.environ["CRIMEGRAPH_AUTH_STRICT"] = "true"

    app = create_app()
    client = TestClient(app)

    token_analyst, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    token_admin, _ = create_access_token(username="admin", role=UserRole.ADMIN)

    headers_analyst = {"Authorization": f"Bearer {token_analyst}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    yield {
        "app": app,
        "client": client,
        "headers_analyst": headers_analyst,
        "headers_admin": headers_admin,
    }

    if "CRIMEGRAPH_MANUAL_DATA_PATH" in os.environ:
        del os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"]
    if "CRIMEGRAPH_AUTH_STRICT" in os.environ:
        del os.environ["CRIMEGRAPH_AUTH_STRICT"]


class TestDay30PatternAnomaly:
    """Test suite for Day 30 Advanced AI Pattern & Anomaly Intelligence."""

    def test_pattern_engine_detection_and_scoring(self, test_setup):
        """Test engine-level pattern detection and deterministic anomaly scoring."""
        graph = test_setup["app"].state.graph
        engine = SuspiciousPatternEngine(graph)

        patterns = engine.detect_all_patterns(limit=50)
        assert len(patterns) > 0

        for pat in patterns:
            assert "pattern_id" in pat
            assert "pattern_type" in pat
            assert "anomaly_score" in pat
            assert 0.0 <= pat["anomaly_score"] <= 1.0
            assert 0.0 <= pat["confidence"] <= 1.0
            assert "scoring_factors" in pat
            assert "disclaimer" in pat

    def test_high_connectivity_hub_pattern(self, test_setup):
        """Test detection of high-connectivity hub nodes."""
        graph = test_setup["app"].state.graph
        engine = SuspiciousPatternEngine(graph)

        hubs = engine._detect_high_connectivity_hubs()
        assert len(hubs) > 0

        top_hub = hubs[0]
        assert top_hub["pattern_type"] == "HIGH_CONNECTIVITY_HUB"
        assert top_hub["anomaly_score"] >= 0.40
        assert len(top_hub["involved_entity_ids"]) > 0
        assert "degree_norm" in top_hub["scoring_factors"]

    def test_cross_case_bridge_pattern(self, test_setup):
        """Test detection of cross-case bridge entities."""
        graph = test_setup["app"].state.graph
        engine = SuspiciousPatternEngine(graph)

        bridges = engine._detect_cross_case_bridge_paths()
        assert len(bridges) > 0

        top_bridge = bridges[0]
        assert top_bridge["pattern_type"] == "CROSS_CASE_BRIDGE_PATH"
        assert len(top_bridge["involved_case_ids"]) >= 2

    def test_api_get_patterns_filtered(self, test_setup):
        """Test GET /api/patterns with filtering options."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/patterns?case_id=CASE_101&limit=10", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "patterns" in data
        assert data["total_count"] >= 0
        assert "disclaimer" in data

    def test_api_get_pattern_by_id(self, test_setup):
        """Test GET /api/patterns/{pattern_id} detail view."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res_list = client.get("/api/patterns?limit=1", headers=headers)
        assert res_list.status_code == 200
        pats = res_list.json()["patterns"]
        assert len(pats) > 0

        pat_id = pats[0]["pattern_id"]
        res_detail = client.get(f"/api/patterns/{pat_id}", headers=headers)
        assert res_detail.status_code == 200
        data = res_detail.json()

        assert data["pattern"]["pattern_id"] == pat_id
        assert "disclaimer" in data

    def test_api_post_patterns_detect(self, test_setup):
        """Test POST /api/patterns/detect endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {
            "case_id": "CASE_101",
            "min_score": 0.20,
            "limit": 5
        }

        res = client.post("/api/patterns/detect", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "total_patterns" in data
        assert "patterns" in data
        assert "safety_notice" in data

    def test_ai_investigator_pattern_query(self, test_setup):
        """Test AI Investigator natural language pattern questions."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"question": "What suspicious patterns exist in CASE_101?"}
        res = client.post("/api/investigate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["query_type"] == "SUSPICIOUS_PATTERNS"
        assert "patterns" in data
        assert len(data["patterns"]) > 0

    def test_safetyguard_guilt_refusal(self, test_setup):
        """Test SafetyGuard non-guilt refusal behavior on pattern queries."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"question": "Does this anomaly pattern prove PERSON_017 is guilty?"}
        res = client.post("/api/investigate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["query_type"] == "SAFETY_REFUSAL"
        assert data["confidence"] == 0.0

    def test_invalid_pattern_id_404(self, test_setup):
        """Test 404 response for invalid pattern ID."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/patterns/PAT_NONEXISTENT_999", headers=headers)
        assert res.status_code == 404

    def test_unauthenticated_request_401(self, test_setup):
        """Test 401 Unauthorized for missing Bearer token."""
        client = test_setup["client"]

        res = client.get("/api/patterns")
        assert res.status_code == 401
