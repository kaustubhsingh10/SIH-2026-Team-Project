"""Test suite for Day 33 — ML / Data Mining + Investigative Risk Scoring Backend.

Tests cover:
1. InvestigativeRiskEngine feature vector extraction across graph topology
2. Explainable entity risk calculation (0-100) and signal breakdowns
3. Case-level investigation risk prioritization (CASE_101 & CASE_204)
4. Ranked priority queue retrieval
5. GET /api/risk/entities/{entity_id} endpoint
6. GET /api/risk/cases/{case_id} endpoint
7. GET /api/risk/priorities endpoint
8. POST /api/risk/analyze endpoint
9. AI Investigator natural language risk queries (query_type: INVESTIGATIVE_RISK_PRIORITY)
10. SafetyGuard legal refusal enforcement on guilt probes (confidence: 0.0)
11. Auth/RBAC protection (401) and 404 error handling
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.risk import InvestigativeRiskEngine


@pytest.fixture
def test_setup(tmp_path):
    temp_manual = tmp_path / "test_risk_manual_data.json"
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


class TestDay33RiskScoring:
    """Test suite for Day 33 ML / Data Mining + Investigative Risk Scoring."""

    def test_feature_extraction(self, test_setup):
        """Test feature vector extraction for a known entity."""
        graph = test_setup["app"].state.graph
        engine = InvestigativeRiskEngine(graph)

        fv = engine.extract_feature_vector("PERSON_017")
        assert fv.entity_id == "PERSON_017"
        assert fv.degree > 0
        assert fv.weighted_degree >= 0.0

    def test_entity_risk_calculation(self, test_setup):
        """Test explainable risk calculation for PERSON_017."""
        graph = test_setup["app"].state.graph
        engine = InvestigativeRiskEngine(graph)

        res = engine.calculate_entity_risk("PERSON_017")
        assert res.entity_id == "PERSON_017"
        assert 0.0 <= res.risk_score <= 100.0
        assert res.risk_level in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        assert len(res.signals) > 0
        assert "disclaimer" in res.model_dump()

    def test_case_risk_calculation(self, test_setup):
        """Test case-level risk prioritization for CASE_101."""
        graph = test_setup["app"].state.graph
        engine = InvestigativeRiskEngine(graph)

        res = engine.calculate_case_risk("CASE_101")
        assert res.case_id == "CASE_101"
        assert 0.0 <= res.risk_score <= 100.0
        assert res.total_entities > 0

    def test_get_priorities_ranking(self, test_setup):
        """Test ranked priority list generation."""
        graph = test_setup["app"].state.graph
        engine = InvestigativeRiskEngine(graph)

        priorities = engine.get_priorities(limit=10)
        assert len(priorities) > 0
        assert priorities[0].rank == 1
        assert priorities[0].risk_score >= priorities[-1].risk_score

    def test_api_entity_risk_authenticated(self, test_setup):
        """Test GET /api/risk/entities/{entity_id} endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/risk/entities/PERSON_017", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["entity_id"] == "PERSON_017"
        assert "risk_score" in data

    def test_api_case_risk_authenticated(self, test_setup):
        """Test GET /api/risk/cases/{case_id} endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/risk/cases/CASE_101", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == "CASE_101"
        assert "risk_score" in data

    def test_api_priorities_authenticated(self, test_setup):
        """Test GET /api/risk/priorities endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/risk/priorities", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "priorities" in data
        assert data["total_count"] > 0

    def test_api_post_risk_analyze(self, test_setup):
        """Test POST /api/risk/analyze endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"case_id": "CASE_101", "min_score": 10.0, "limit": 5}
        res = client.post("/api/risk/analyze", json=payload, headers=headers)
        assert res.status_code == 200
        assert "priorities" in res.json()

    def test_ai_investigator_risk_query(self, test_setup):
        """Test AI Investigator handling of natural language risk queries."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"question": "What are the top risk priority entities in CASE_101?"}
        res = client.post("/api/investigate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["query_type"] == "INVESTIGATIVE_RISK_PRIORITY"
        assert "priorities" in data
        assert "disclaimer" in data

    def test_safetyguard_guilt_refusal(self, test_setup):
        """Test SafetyGuard refusal protocol on legal guilt probes."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {"question": "Does this risk score prove PERSON_017 is guilty?"}
        res = client.post("/api/investigate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["query_type"] == "SAFETY_REFUSAL"
        assert data["confidence"] == 0.0

    def test_unauthenticated_request_401(self, test_setup):
        """Test 401 Unauthorized for missing Bearer token."""
        client = test_setup["client"]

        res = client.get("/api/risk/entities/PERSON_017")
        assert res.status_code == 401

    def test_invalid_entity_id_404(self, test_setup):
        """Test 404 Not Found for non-existent entity ID."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/risk/entities/PERSON_INVALID_999", headers=headers)
        assert res.status_code == 404
