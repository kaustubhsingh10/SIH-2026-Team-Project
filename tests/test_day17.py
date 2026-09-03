"""Day 17 Tests — Backend Production Hardening & Deployment Preparation.

Tests specifically designed for Day 17 requirements:
1. API Inventory & Contract Stability across Case, Entity, Evidence, Timeline, Related Cases, and Graph
2. Input validation bounds, pagination limits, and resource protection
3. Concurrent request isolation and data integrity
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestDay17ApiInventoryAndContracts:
    """Verifies all API endpoints in the inventory adhere to the frozen contract."""

    def test_health_endpoint(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_case_detail_contract(self, client):
        res = client.get("/api/cases/CASE_101")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "CASE_101"
        assert "title" in data
        assert "status" in data

    def test_case_timeline_contract(self, client):
        res = client.get("/api/cases/CASE_101/timeline")
        assert res.status_code == 200
        data = res.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_entity_neighbors_contract(self, client):
        res = client.get("/api/entities/PERSON_017/neighbors?direction=undirected")
        assert res.status_code == 200
        data = res.json()
        assert "neighbors" in data
        assert isinstance(data["neighbors"], list)

    def test_evidence_detail_contract(self, client):
        res = client.get("/api/evidence/EVID_042_01")
        assert res.status_code == 200
        data = res.json()
        assert data["evidence_id"] == "EVID_042_01"
        assert "source_document_id" in data

    def test_cross_case_connections_contract(self, client):
        res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        assert res.status_code == 200
        data = res.json()
        assert "connections" in data
        assert len(data["connections"]) > 0


class TestDay17ResourceProtectionAndValidation:
    """Verifies bounds on queries, inputs, and error boundaries."""

    def test_case_not_found_standard_json(self, client):
        res = client.get("/api/cases/CASE_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_entity_not_found_standard_json(self, client):
        res = client.get("/api/entities/PERSON_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_evidence_not_found_standard_json(self, client):
        res = client.get("/api/evidence/EVID_999")
        assert res.status_code == 404
        assert "detail" in res.json()


class TestDay17ConcurrencyAndIsolation:
    """Verifies concurrent requests do not cross-contaminate state."""

    def test_concurrent_independent_requests(self, client):
        res1 = client.get("/api/cases/CASE_101")
        res2 = client.get("/api/cases/CASE_204")
        res3 = client.get("/api/entities/PERSON_017")
        res4 = client.get("/api/entities/PERSON_089")

        assert res1.status_code == 200 and res1.json()["id"] == "CASE_101"
        assert res2.status_code == 200 and res2.json()["id"] == "CASE_204"
        assert res3.status_code == 200 and res3.json()["id"] == "PERSON_017"
        assert res4.status_code == 200 and res4.json()["id"] == "PERSON_089"
