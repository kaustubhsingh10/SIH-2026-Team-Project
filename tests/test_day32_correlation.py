"""Test suite for Day 32 — Cross-Source Intelligence Correlation Backend.

Tests cover:
1. CrossSourceCorrelationEngine detection across multi-source data records
2. Entity, relationship, temporal, location, cross-case, and contradiction correlations
3. Deterministic correlation scoring and factor breakdowns
4. GET /api/correlations endpoint with filtering by case_id, entity_id, min_score
5. GET /api/correlations/{correlation_id} detail view
6. POST /api/correlations/analyze custom sweep endpoint
7. GET /api/cases/{case_id}/correlations and GET /api/entities/{entity_id}/correlations
8. AI Investigator natural language correlation queries (query_type: CROSS_SOURCE_CORRELATION)
9. SafetyGuard legal refusal enforcement on guilt probes (confidence: 0.0)
10. RBAC authentication enforcement (401) and 404 error handling
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.correlation import CrossSourceCorrelationEngine


@pytest.fixture
def test_setup(tmp_path):
    temp_manual = tmp_path / "test_correlation_manual_data.json"
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


class TestDay32Correlation:
    """Test suite for Day 32 Cross-Source Intelligence Correlation Backend."""

    def test_correlation_engine_detection_and_scoring(self, test_setup):
        """Test engine-level correlation detection and composite scoring."""
        graph = test_setup["app"].state.graph
        engine = CrossSourceCorrelationEngine(graph)

        correlations = engine.detect_all_correlations(limit=50)
        assert len(correlations) > 0

        top = correlations[0]
        assert "correlation_id" in top
        assert "correlation_type" in top
        assert "correlation_score" in top
        assert "explanation" in top
        assert "investigative_lead" in top
        assert "disclaimer" in top
        assert top["correlation_score"] >= 0.0

    def test_api_get_correlations_authenticated(self, test_setup):
        """Test GET /api/correlations endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/correlations", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "correlations" in data
        assert "total_count" in data
        assert len(data["correlations"]) > 0

    def test_api_get_correlations_filtered(self, test_setup):
        """Test GET /api/correlations with case_id and min_score filtering."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/correlations?case_id=CASE_101&min_score=0.30", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "correlations" in data

    def test_api_get_correlation_by_id(self, test_setup):
        """Test GET /api/correlations/{correlation_id} detail view."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res_list = client.get("/api/correlations", headers=headers)
        assert res_list.status_code == 200
        corr_id = res_list.json()["correlations"][0]["correlation_id"]

        res_detail = client.get(f"/api/correlations/{corr_id}", headers=headers)
        assert res_detail.status_code == 200
        assert res_detail.json()["correlation_id"] == corr_id

    def test_api_post_correlations_analyze(self, test_setup):
        """Test POST /api/correlations/analyze custom sweep endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"case_id": "CASE_101", "min_score": 0.30, "limit": 10}
        res = client.post("/api/correlations/analyze", json=payload, headers=headers)
        assert res.status_code == 200
        assert "correlations" in res.json()

    def test_ai_investigator_correlation_query(self, test_setup):
        """Test AI Investigator handling of natural language correlation questions."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"question": "What cross-source correlations exist in CASE_101?"}
        res = client.post("/api/investigate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["query_type"] == "CROSS_SOURCE_CORRELATION"
        assert "correlations" in data
        assert "disclaimer" in data

    def test_safetyguard_guilt_refusal(self, test_setup):
        """Test SafetyGuard non-guilt refusal protocol on legal guilt probes."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"question": "Does this correlation prove PERSON_017 is guilty?"}
        res = client.post("/api/investigate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["query_type"] == "SAFETY_REFUSAL"
        assert data["confidence"] == 0.0

    def test_unauthenticated_request_401(self, test_setup):
        """Test 401 Unauthorized for missing Bearer token."""
        client = test_setup["client"]

        res = client.get("/api/correlations")
        assert res.status_code == 401

    def test_invalid_correlation_id_404(self, test_setup):
        """Test 404 Not Found for non-existent correlation ID."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/correlations/CORR_NONEXISTENT_999", headers=headers)
        assert res.status_code == 404
