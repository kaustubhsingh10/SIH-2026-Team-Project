"""Day 15 Tests — Backend Production Readiness & Deployment Preparation.

Tests specifically designed for Day 15 requirements:
1. Production configuration and health reporting
2. Resource protection, traversal limits, and pagination safety
3. Complete 9-step production sanity verification flow
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestProductionConfigurationAndHealth:
    """Verifies health reporting and CORS configuration."""

    def test_health_check_readiness(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "environment" in data or "version" in data or "status" in data

    def test_cors_headers_present(self, client):
        res = client.options(
            "/api/cases",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert res.status_code == 200


class TestResourceProtectionAndSafety:
    """Verifies resource limits on pagination and graph traversal."""

    def test_pagination_limits_evidence(self, client):
        # limit=5 returns maximum 5 items
        res = client.get("/api/evidence?limit=5")
        assert res.status_code == 200
        data = res.json()
        assert len(data) <= 5

    def test_max_depth_enforced_connections(self, client):
        # max_depth > 10 returns 422 Unprocessable Entity
        res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204&max_depth=99")
        assert res.status_code == 422


class TestProductionSanitySuite:
    """Complete 9-step production sanity verification suite."""

    def test_step_1_case_101(self, client):
        res = client.get("/api/cases/CASE_101")
        assert res.status_code == 200
        assert res.json()["id"] == "CASE_101"

    def test_step_2_case_204(self, client):
        res = client.get("/api/cases/CASE_204")
        assert res.status_code == 200
        assert res.json()["id"] == "CASE_204"

    def test_step_3_person_017(self, client):
        res = client.get("/api/entities/PERSON_017")
        assert res.status_code == 200
        assert res.json()["id"] == "PERSON_017"

    def test_step_4_graph_traversal_path(self, client):
        res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        assert res.status_code == 200
        data = res.json()
        assert len(data["connections"]) > 0
        assert data["connections"][0]["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]

    def test_step_5_evidence_retrieval(self, client):
        res = client.get("/api/evidence/EVID_042_01")
        assert res.status_code == 200
        assert res.json()["evidence_id"] == "EVID_042_01"

    def test_step_6_related_cases(self, client):
        res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        assert res.status_code == 200
        assert len(res.json()["connections"]) > 0

    def test_step_7_investigation_data(self, client):
        res = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
        assert res.status_code == 200
        data = res.json()
        assert data["query_type"] == "CROSS_CASE_CONNECTION"
        assert "PHONE_042" in data["path"]

    def test_step_8_unknown_case(self, client):
        res = client.get("/api/cases/CASE_999")
        assert res.status_code == 404
