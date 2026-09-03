"""Day 12 Tests — Backend Hardening, Input Resilience, Repeated Demo Stability, and Final SIH Readiness.

Tests specifically designed for Day 12 requirements:
1. Repeated SIH demonstration stability & determinism
2. Boundary inputs, long strings, and special characters
3. Search and filter edge cases
4. Lifecycle stability and clean recovery
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


class TestRepeatedDemoAndConsistency:
    """Verifies that repeated queries and traversals remain deterministic across multiple runs."""

    def test_repeated_cross_case_pathfinding(self, client):
        expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        for _ in range(10):
            res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
            assert res.status_code == 200
            data = res.json()
            assert len(data["connections"]) > 0
            assert data["connections"][0]["path"] == expected_path
            assert data["connections"][0]["confidence"] == 0.93

    def test_repeated_investigation_queries(self, client):
        for _ in range(5):
            res = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
            assert res.status_code == 200
            data = res.json()
            assert data["query_type"] == "CROSS_CASE_CONNECTION"
            assert data["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]


class TestBoundaryInputHardening:
    """Verifies backend resilience against boundary values, long strings, and special characters."""

    def test_long_string_entity_search(self, client):
        long_query = "A" * 1000
        res = client.get(f"/api/entities?search={long_query}")
        assert res.status_code == 200
        assert res.json() == []

    def test_special_characters_case_id(self, client):
        res = client.get("/api/cases/CASE_!@#$%^&*()")
        assert res.status_code == 404

    def test_special_characters_investigate_query(self, client):
        res = client.post("/api/investigate", json={"question": "!@#$%^&*()<>{}[]/\\`~"})
        assert res.status_code == 200
        assert "answer" in res.json()


class TestSearchAndFilterSanity:
    """Verifies entity, case, and evidence filtering robustness."""

    def test_case_insensitive_entity_type_filter(self, client):
        res_upper = client.get("/api/entities?type=PERSON")
        res_lower = client.get("/api/entities?type=person")
        assert res_upper.status_code == 200
        assert res_lower.status_code == 200
        assert len(res_upper.json()) == len(res_lower.json())

    def test_evidence_filtering_bounds(self, client):
        # min_confidence > 1.0 is rejected with 422 Unprocessable Entity
        res_invalid = client.get("/api/evidence?min_confidence=1.5")
        assert res_invalid.status_code == 422
        # min_confidence=0.99 returns empty array or subset
        res_valid = client.get("/api/evidence?min_confidence=0.99")
        assert res_valid.status_code == 200
        assert isinstance(res_valid.json(), list)
