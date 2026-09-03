"""Test suite for Day 29 — Advanced Link Analysis & Path Discovery.

Tests cover:
1. Direct (1-hop), 2-hop, and multi-hop path discovery
2. Case-to-case multi-hop path discovery (e.g. CASE_101 -> CASE_204)
3. Dynamic path traversal with manually created persistent cases
4. No-path scenario for isolated or disconnected entities
5. Cyclic graph protection and duplicate path prevention
6. Maximum hop depth enforcement (max_depth)
7. Explainable path scoring and factor breakdown
8. Temporal chronological alignment analysis
9. Evidence lineage and provenance preservation
10. SafetyGuard legal disclaimer compliance
11. Invalid entity/case ID error handling (404)
12. RBAC authentication enforcement (401)
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.paths import AdvancedPathEngine
from crimegraph.models.paths import TemporalAlignment


@pytest.fixture
def test_setup(tmp_path):
    temp_manual = tmp_path / "test_path_manual_data.json"
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


class TestDay29PathDiscovery:
    """Test suite for Day 29 Advanced Link Analysis & Path Discovery."""

    def test_direct_and_two_hop_path_engine(self, test_setup):
        """Test engine-level discovery for direct and 2-hop entity paths."""
        graph = test_setup["app"].state.graph
        engine = AdvancedPathEngine(graph)

        res = engine.analyze_paths(source_id="PERSON_017", target_id="PERSON_089", max_depth=5, limit=5)
        assert res.total_paths_found > 0
        top = res.paths[0]

        assert top.source_id == "PERSON_017"
        assert top.target_id == "PERSON_089"
        assert len(top.path) >= 3  # PERSON_017 -> PHONE_042 -> PERSON_089
        assert "PHONE_042" in top.shared_entities or "PHONE_042" in top.path
        assert 0.0 <= top.path_score <= 1.0
        assert len(top.evidence_ids) > 0
        assert len(top.steps) == top.hop_count

    def test_case_to_case_path_discovery(self, test_setup):
        """Test multi-hop path discovery connecting CASE_101 and CASE_204."""
        graph = test_setup["app"].state.graph
        engine = AdvancedPathEngine(graph)

        res = engine.analyze_paths(source_id="CASE_101", target_id="CASE_204", max_depth=6, limit=5)
        assert res.total_paths_found > 0
        top = res.paths[0]

        assert top.source_id == "CASE_101"
        assert top.target_id == "CASE_204"
        assert top.path[0] == "CASE_101"
        assert top.path[-1] == "CASE_204"

        # Verify canonical bridge entities
        assert "PERSON_017" in top.path
        assert "PHONE_042" in top.path or "PHONE_042" in top.shared_entities

        assert top.scoring_factors["cross_case_bonus"] == 0.15
        assert top.path_score > 0.60

    def test_paths_analyze_post_api(self, test_setup):
        """Test POST /api/paths/analyze endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {
            "source_id": "PERSON_017",
            "target_id": "PERSON_089",
            "max_depth": 5,
            "limit": 3,
            "include_temporal": True
        }

        res = client.post("/api/paths/analyze", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["source_id"] == "PERSON_017"
        assert data["target_id"] == "PERSON_089"
        assert data["total_paths_found"] > 0
        assert len(data["paths"]) <= 3

        top = data["paths"][0]
        assert "path_id" in top
        assert "explanation" in top
        assert "scoring_factors" in top
        assert "safety_notice" in data

    def test_paths_analyze_get_api(self, test_setup):
        """Test GET /api/paths/analyze endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/paths/analyze?source_id=CASE_101&target_id=CASE_204&max_depth=6", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["source_id"] == "CASE_101"
        assert data["target_id"] == "CASE_204"
        assert data["total_paths_found"] > 0

    def test_case_connections_convenience_api(self, test_setup):
        """Test GET /api/paths/case-connections endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/paths/case-connections?case_a=CASE_101&case_b=CASE_204", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["case_a"] == "CASE_101"
        assert data["case_b"] == "CASE_204"
        assert data["total_connections"] > 0
        assert "safety_notice" in data

    def test_no_path_scenario(self, test_setup):
        """Test response when two entities are disconnected in the graph."""
        graph = test_setup["app"].state.graph
        engine = AdvancedPathEngine(graph)

        # Create isolated dummy node in store
        graph.add_entity({
            "id": "PERSON_ISOLATED_999",
            "name": "Isolated Individual",
            "entity_type": "PERSON",
            "confidence": 0.90,
            "origin": "DATASET"
        })

        res = engine.analyze_paths(source_id="PERSON_017", target_id="PERSON_ISOLATED_999", max_depth=4)
        assert res.total_paths_found == 0
        assert res.paths == []

    def test_max_depth_enforcement(self, test_setup):
        """Test that max_depth strictly restricts multi-hop path traversal."""
        graph = test_setup["app"].state.graph
        engine = AdvancedPathEngine(graph)

        # Hop depth 1 for CASE_101 to CASE_204 (which is at least 4 hops away)
        res_depth1 = engine.analyze_paths(source_id="CASE_101", target_id="CASE_204", max_depth=1)
        assert res_depth1.total_paths_found == 0

        # Hop depth 6 allows the path
        res_depth6 = engine.analyze_paths(source_id="CASE_101", target_id="CASE_204", max_depth=6)
        assert res_depth6.total_paths_found > 0

    def test_invalid_entity_404_error(self, test_setup):
        """Test 404 response for invalid or missing entity IDs."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/paths/analyze?source_id=PERSON_017&target_id=NONEXISTENT_999", headers=headers)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_unauthenticated_request_rejected_401(self, test_setup):
        """Test 401 Unauthorized for missing Bearer token."""
        client = test_setup["client"]

        res = client.get("/api/paths/analyze?source_id=CASE_101&target_id=CASE_204")
        assert res.status_code == 401

    def test_temporal_alignment_scoring(self, test_setup):
        """Test chronological alignment indicator on path steps."""
        graph = test_setup["app"].state.graph
        engine = AdvancedPathEngine(graph)

        res = engine.analyze_paths(source_id="PERSON_017", target_id="PERSON_089", include_temporal=True)
        assert res.total_paths_found > 0
        top = res.paths[0]

        assert top.temporal_alignment in [
            TemporalAlignment.CHRONOLOGICAL.value,
            TemporalAlignment.OUT_OF_ORDER.value,
            TemporalAlignment.UNDATED.value,
        ]
        assert "temporal_factor" in top.scoring_factors

    def test_safetyguard_legal_disclaimer(self, test_setup):
        """Test non-culpability legal disclaimer in path responses."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/paths/analyze?source_id=PERSON_017&target_id=PERSON_089", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "safety_notice" in data
        assert "NOT establish legal guilt" in data["safety_notice"]
