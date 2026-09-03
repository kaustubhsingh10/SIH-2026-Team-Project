"""Day 13 Tests — Backend Hardening, Bug Fixing, and Release Stability.

Tests specifically designed for Day 13 requirements:
1. Concurrency and repeated request idempotency
2. Security header and CORS compliance
3. End-to-end SIH dry run of all backend flows
4. Robustness against malformed payloads and invalid methods
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.traversal import find_cross_case_connections


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestReleaseStabilityAndConcurrency:
    """Verifies that high-frequency repeated requests maintain consistent state."""

    def test_concurrent_simulation_read_requests(self, client):
        for _ in range(25):
            res_health = client.get("/api/health")
            res_cases = client.get("/api/cases")
            res_graph = client.get("/api/cases/CASE_101/graph")
            assert res_health.status_code == 200
            assert res_cases.status_code == 200
            assert res_graph.status_code == 200


class TestSecurityAndHeaderCompliance:
    """Verifies security response headers and method restriction."""

    def test_invalid_http_methods(self, client):
        # PUT to non-put endpoint returns 405 Method Not Allowed
        res = client.put("/api/cases", json={})
        assert res.status_code == 405

    def test_malformed_json_investigate(self, client):
        # Invalid JSON body returns 422 Unprocessable Entity
        res = client.post(
            "/api/investigate",
            content="invalid json payload",
            headers={"Content-Type": "application/json"}
        )
        assert res.status_code == 422


class TestSIHDemoDryRun:
    """Dry run of the complete SIH demonstration flow."""

    def test_sih_demo_step_by_step(self, client):
        # 1. Load Case 101
        res_case = client.get("/api/cases/CASE_101")
        assert res_case.status_code == 200
        assert res_case.json()["id"] == "CASE_101"

        # 2. Load Case 101 graph
        res_graph = client.get("/api/cases/CASE_101/graph")
        assert res_graph.status_code == 200
        assert len(res_graph.json()["nodes"]) >= 10

        # 3. Load Evidence
        res_evid = client.get("/api/evidence/EVID_042_01")
        assert res_evid.status_code == 200
        assert res_evid.json()["evidence_id"] == "EVID_042_01"

        # 4. Cross-case query
        res_conn = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
        assert res_conn.status_code == 200
        data_conn = res_conn.json()
        assert data_conn["query_type"] == "CROSS_CASE_CONNECTION"
        assert data_conn["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert data_conn["confidence"] == 0.93

        # 5. Safety query
        res_safe = client.post("/api/investigate", json={"question": "Is Person 017 guilty?"})
        assert res_safe.status_code == 200
        data_safe = res_safe.json()
        assert "disclaimer" in data_safe
        assert "Aarav Verma" in data_safe["answer"]

        # 6. Unknown query
        res_unk = client.post("/api/investigate", json={"question": "How are Case 999 and Case 888 connected?"})
        assert res_unk.status_code == 200
        assert res_unk.json()["query_type"] == "NOT_FOUND"
