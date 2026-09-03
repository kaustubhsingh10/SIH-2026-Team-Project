"""Day 8 Tests — Backend Robustness, Production Readiness, and Input Validation.

Tests specifically designed for Day 8 requirements:
1. Input sanitization and whitespace tolerance
2. Standardized 404 not-found responses across all resource endpoints
3. Health check and readiness reporting
4. Configurable dataset environment resolution
5. Main demonstration graph and safety regressions
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import get_default_dataset_path, load_dataset
from crimegraph.graph.traversal import find_cross_case_connections


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def graph():
    return load_dataset()


class TestInputSanitizationAndValidation:
    """Verifies that API endpoints gracefully handle whitespace and casing in parameters."""

    def test_case_details_whitespace_tolerant(self, client):
        res = client.get("/api/cases/  CASE_101  ")
        assert res.status_code == 200
        assert res.json()["id"] == "CASE_101"

    def test_case_graph_whitespace_tolerant(self, client):
        res = client.get("/api/cases/  CASE_101  /graph")
        assert res.status_code == 200
        assert "nodes" in res.json()
        assert "edges" in res.json()

    def test_case_entities_whitespace_tolerant(self, client):
        res = client.get("/api/cases/  CASE_101  /entities?entity_type=person")
        assert res.status_code == 200
        nodes = res.json()
        assert len(nodes) > 0
        for node in nodes:
            assert node["entity_type"] == "PERSON"

    def test_case_connections_whitespace_tolerant(self, client):
        res = client.get("/api/cases/connections?case_a=  CASE_101  &case_b=  CASE_204  ")
        assert res.status_code == 200
        conns = res.json()["connections"]
        assert len(conns) > 0
        assert conns[0]["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]

    def test_entity_details_whitespace_tolerant(self, client):
        res = client.get("/api/entities/  PERSON_017  ")
        assert res.status_code == 200
        assert res.json()["id"] == "PERSON_017"
        assert res.json()["name"] == "Aarav Verma"

    def test_entity_neighbors_whitespace_tolerant(self, client):
        res = client.get("/api/entities/  PERSON_017  /neighbors")
        assert res.status_code == 200
        assert res.json()["neighbor_count"] > 0

    def test_evidence_item_whitespace_tolerant(self, client):
        res = client.get("/api/evidence/  EVID_042_01  ")
        assert res.status_code == 200
        assert res.json()["evidence_id"] == "EVID_042_01"

    def test_paths_whitespace_tolerant(self, client):
        res = client.get("/api/paths?source_id=  PERSON_017  &target_id=  PERSON_089  ")
        assert res.status_code == 200
        paths = res.json()["paths"]
        assert len(paths) > 0


class TestNotFoundStandardization:
    """Verifies that all nonexistent resources return clean HTTP 404 with structured error bodies."""

    def test_nonexistent_case_returns_404(self, client):
        res = client.get("/api/cases/CASE_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_case_graph_returns_404(self, client):
        res = client.get("/api/cases/CASE_999/graph")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_case_entities_returns_404(self, client):
        res = client.get("/api/cases/CASE_999/entities")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_case_timeline_returns_404(self, client):
        res = client.get("/api/cases/CASE_999/timeline")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_entity_returns_404(self, client):
        res = client.get("/api/entities/PERSON_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_entity_neighbors_returns_404(self, client):
        res = client.get("/api/entities/PERSON_999/neighbors")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_evidence_returns_404(self, client):
        res = client.get("/api/evidence/EVID_999")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_path_source_returns_404(self, client):
        res = client.get("/api/paths?source_id=INVALID_SRC&target_id=PERSON_089")
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_nonexistent_path_target_returns_404(self, client):
        res = client.get("/api/paths?source_id=PERSON_017&target_id=INVALID_TGT")
        assert res.status_code == 404
        assert "detail" in res.json()


class TestHealthAndEnvironmentConfig:
    """Verifies backend health reporting and deployment environment configuration."""

    def test_health_check_status_healthy(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    def test_root_status_reports_metrics(self, client):
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "operational"
        assert "metrics" in data
        assert data["metrics"]["entity_count"] > 0
        assert data["metrics"]["relationship_count"] > 0
        assert data["metrics"]["evidence_count"] > 0

    def test_custom_data_path_environment_variable(self, monkeypatch):
        test_path = "/tmp/custom_crimegraph_data.json"
        monkeypatch.setenv("CRIMEGRAPH_DATA_PATH", test_path)
        resolved = get_default_dataset_path()
        assert resolved == Path(test_path)


class TestMainDemoAndSafetyPreservation:
    """Verifies that the core SIH demonstration and safety disclaimers remain fully intact."""

    def test_main_demo_path_cross_case(self, graph):
        conns = find_cross_case_connections(graph, "CASE_101", "CASE_204")
        assert len(conns) > 0
        assert conns[0]["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert conns[0]["shared_entities"] == ["PHONE_042"]
        assert conns[0]["confidence"] == 0.93

    def test_safety_question_no_guilt_verdict(self, client):
        res = client.post("/api/investigate", json={"question": "Is Person 017 guilty?"})
        assert res.status_code == 200
        data = res.json()
        assert "disclaimer" in data
        assert "guilty" not in data["answer"].lower() or "investigative lead" in data["disclaimer"].lower()

    def test_nonexistent_investigation_returns_not_found(self, client):
        res = client.post("/api/investigate", json={"question": "How are Case 999 and Case 888 connected?"})
        assert res.status_code == 200
        assert res.json()["query_type"] == "NOT_FOUND"
