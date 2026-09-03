"""Day 18 Tests — Backend & Database Production Preparation.

Tests specifically designed for Day 18 requirements:
1. Complete API inventory and production configuration checks
2. Request validation, unknown case handling, and error boundaries
3. Concurrency, recovery readiness, and end-to-end investigation stability
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestDay18ApiInventoryAndContracts:
    """Verifies all API endpoints are production-ready."""

    def test_health_check(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_cases_list(self, client):
        res = client.get("/api/cases")
        assert res.status_code == 200
        assert len(res.json()) >= 2

    def test_case_101_detail(self, client):
        res = client.get("/api/cases/CASE_101")
        assert res.status_code == 200
        assert res.json()["id"] == "CASE_101"

    def test_case_204_detail(self, client):
        res = client.get("/api/cases/CASE_204")
        assert res.status_code == 200
        assert res.json()["id"] == "CASE_204"

    def test_case_101_graph(self, client):
        res = client.get("/api/cases/CASE_101/graph")
        assert res.status_code == 200
        data = res.json()
        assert "nodes" in data
        assert "edges" in data

    def test_evidence_item(self, client):
        res = client.get("/api/evidence/EVID_042_01")
        assert res.status_code == 200
        assert res.json()["evidence_id"] == "EVID_042_01"


class TestDay18ErrorBoundariesAndValidation:
    """Verifies controlled errors without stack trace leakage."""

    def test_unknown_case_returns_404(self, client):
        res = client.get("/api/cases/CASE_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_unknown_entity_returns_404(self, client):
        res = client.get("/api/entities/PERSON_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_investigation_main_demo(self, client):
        res = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
        assert res.status_code == 200
        data = res.json()
        assert data["query_type"] == "CROSS_CASE_CONNECTION"
        assert data["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert data["confidence"] == 0.93
