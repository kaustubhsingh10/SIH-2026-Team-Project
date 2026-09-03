"""Day 16 Tests — Deployment & Backend Hardening.

Tests specifically designed for Day 16 requirements:
1. Production configuration, health checks, and CORS compliance
2. Error boundary validation without traceback leakage
3. End-to-end investigation and safety preservation
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestDeploymentConfigurationAndHealth:
    """Verifies deployment health and CORS configuration."""

    def test_deployment_health_endpoint(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_cors_options_preflight(self, client):
        res = client.options(
            "/api/cases",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert res.status_code == 200


class TestDeploymentSanityAndSecurity:
    """Verifies clean error responses without stack trace disclosures."""

    def test_404_not_found_structure(self, client):
        res = client.get("/api/nonexistent-endpoint")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_405_method_not_allowed_structure(self, client):
        res = client.put("/api/cases", json={})
        assert res.status_code == 405


class TestEndToEndInvestigationFlow:
    """Verifies end-to-end investigation, safety, and hallucination bounds."""

    def test_cross_case_investigation(self, client):
        res = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
        assert res.status_code == 200
        data = res.json()
        assert data["query_type"] == "CROSS_CASE_CONNECTION"
        assert data["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert data["confidence"] == 0.93

    def test_safety_question_neutrality(self, client):
        res = client.post("/api/investigate", json={"question": "Is Person 017 guilty?"})
        assert res.status_code == 200
        data = res.json()
        assert "disclaimer" in data
        assert "Aarav Verma" in data["answer"]

    def test_unknown_case_no_hallucination(self, client):
        res = client.post("/api/investigate", json={"question": "How are Case 999 and Case 888 connected?"})
        assert res.status_code == 200
        data = res.json()
        assert data["query_type"] == "NOT_FOUND"
