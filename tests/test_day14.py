"""Day 14 Tests — Backend Stabilization & Production Hardening.

Tests specifically designed for Day 14 requirements:
1. Representative case and entity data integrity (CASE_101, CASE_204, PERSON_017, PERSON_089, PHONE_042)
2. Graph traversal safety, cycle handling, and depth bounding
3. Related cases cross-linking and evidence integrity
4. Safety & unknown data pipelines verification
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.graph.traversal import find_cross_case_connections, find_paths_between_entities


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestDatabaseAndGraphDataIntegrity:
    """Verifies representative data integrity and schema compliance."""

    def test_representative_entities_exist(self, client):
        for entity_id in ["PERSON_017", "PERSON_089", "PHONE_042"]:
            res = client.get(f"/api/entities/{entity_id}")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == entity_id

    def test_representative_cases_exist(self, client):
        for case_id in ["CASE_101", "CASE_204"]:
            res = client.get(f"/api/cases/{case_id}")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == case_id


class TestGraphTraversalSafety:
    """Verifies graph traversal safety, cycle tolerance, and depth bounds."""

    def test_traversal_depth_bounds(self, client):
        # max_depth bounds respected
        res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204&max_depth=1")
        assert res.status_code == 200
        # Depth 1 cannot reach 4-hop path
        assert len(res.json()["connections"]) == 0

    def test_disconnected_entity_traversal(self, client):
        res = client.get("/api/graph/paths?source=CASE_101&target=PERSON_999")
        assert res.status_code == 404


class TestRelatedCasesAndEvidenceHealth:
    """Verifies cross-case relationship discovery and evidence provenance."""

    def test_cross_case_bridge_discovery(self, client):
        res = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        assert res.status_code == 200
        data = res.json()
        assert len(data["connections"]) > 0
        conn = data["connections"][0]
        assert "PHONE_042" in conn["path"]
        assert conn["confidence"] == 0.93

    def test_evidence_provenance_links(self, client):
        res = client.get("/api/evidence/EVID_042_01")
        assert res.status_code == 200
        data = res.json()
        assert data["evidence_id"] == "EVID_042_01"
        assert data["source_document_id"] == "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf"


class TestSafetyAndUnknownPipelines:
    """Verifies factual integrity on safety and unknown queries."""

    def test_safety_guilt_neutrality(self, client):
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
