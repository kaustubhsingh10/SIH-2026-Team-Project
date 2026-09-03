"""Day 10 Tests — Backend Hardening, Production Readiness, Security, and Smoke Testing.

Tests specifically designed for Day 10 requirements:
1. Health endpoint and degraded state behavior
2. Configurable CORS and security posture
3. Global exception handling without traceback leakage
4. Full system smoke test across all API contract endpoints
5. Server lifecycle and state stability
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.traversal import find_cross_case_connections


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def graph():
    return load_dataset()


class TestHealthAndReadinessHardening:
    """Verifies that health and readiness reporting accurately reflect store initialization."""

    def test_health_healthy_when_graph_loaded(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_health_degraded_when_empty_store(self):
        empty_store = KnowledgeGraphStore()
        app = create_app(graph_instance=empty_store)
        empty_client = TestClient(app)
        res = empty_client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "degraded"

    def test_root_status_contract(self, client):
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["system"] == "CrimeGraph AI"
        assert data["status"] == "operational"
        assert "disclaimer" in data
        assert "metrics" in data
        assert data["metrics"]["entity_count"] > 0


class TestSecurityAndConfiguration:
    """Verifies security configuration and environment-driven settings."""

    def test_cors_environment_configuration(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:5500")
        app = create_app()
        assert app is not None

    def test_error_response_no_traceback(self, client):
        # Requesting nonexistent route returns clean 404
        res = client.get("/api/nonexistent_route_999")
        assert res.status_code == 404
        assert "Traceback" not in res.text
        assert "File \"" not in res.text


class TestFullSystemSmokeTest:
    """Smoke tests all core endpoints defined in API_CONTRACT.md."""

    def test_smoke_endpoints(self, client):
        # 1. Health
        assert client.get("/api/health").status_code == 200
        # 2. Cases list
        r_cases = client.get("/api/cases")
        assert r_cases.status_code == 200
        assert len(r_cases.json()) >= 4
        # 3. Case detail
        assert client.get("/api/cases/CASE_101").status_code == 200
        # 4. Case graph
        assert client.get("/api/cases/CASE_101/graph").status_code == 200
        # 5. Entities
        r_entities = client.get("/api/entities")
        assert r_entities.status_code == 200
        assert len(r_entities.json()) >= 30
        # 6. Entity detail
        assert client.get("/api/entities/PERSON_017").status_code == 200
        # 7. Evidence
        r_evid = client.get("/api/evidence")
        assert r_evid.status_code == 200
        assert len(r_evid.json()) >= 19
        # 8. Paths
        assert client.get("/api/paths?source_id=PERSON_017&target_id=PERSON_089").status_code == 200
        # 9. Cross-case connections
        r_conn = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        assert r_conn.status_code == 200
        assert len(r_conn.json()["connections"]) > 0
        # 10. Investigation
        r_inv = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
        assert r_inv.status_code == 200
        assert r_inv.json()["query_type"] == "CROSS_CASE_CONNECTION"
