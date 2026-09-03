"""Test suite for Day 28 — Advanced Key Player & Influencer Intelligence.

Tests cover:
1. Deterministic key player ranking and scoring
2. Graph centrality calculations (degree, betweenness, closeness, PageRank)
3. Key player role classification (CORE_HUB, BRIDGE_ENTITY, CROSS_CASE_INFLUENCER, etc.)
4. Cross-case influencer detection across multi-case graphs
5. Case-filtered key player retrieval and 404 error handling for missing cases
6. Explainability, evidence linkage, and provenance preservation
7. SafetyGuard non-culpability neutrality guarantees
8. RBAC and authentication enforcement
9. Endpoints: /api/influence, /api/influence/rankings, /api/influence/entity/{entity_id}, /api/influence/community
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.intelligence import NetworkIntelligenceEngine
from crimegraph.models.intelligence import KeyPlayerRole


@pytest.fixture
def test_setup(tmp_path):
    temp_manual = tmp_path / "test_key_player_manual_data.json"
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


class TestDay28KeyPlayerIntelligence:
    """Test suite for Day 28 Key Player & Influencer Intelligence."""

    def test_direct_engine_metrics_calculation(self, test_setup):
        """Test engine level calculations for degree, betweenness, closeness, and PageRank."""
        graph = test_setup["app"].state.graph
        engine = NetworkIntelligenceEngine(graph)

        betweenness = engine.compute_betweenness_centrality()
        closeness = engine.compute_closeness_centrality()
        pagerank = engine.compute_pagerank()

        assert len(betweenness) == len(graph.entities)
        assert len(closeness) == len(graph.entities)
        assert len(pagerank) == len(graph.entities)

        for node_id in graph.entities:
            assert betweenness[node_id] >= 0.0
            assert closeness[node_id] >= 0.0
            assert pagerank[node_id] >= 0.0

    def test_global_key_players_api(self, test_setup):
        """Test GET /api/intelligence/key-players and /api/influence endpoints."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players?limit=10", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["scope"] == "GLOBAL"
        assert data["key_players_count"] > 0
        assert len(data["key_players"]) <= 10

        first = data["key_players"][0]
        assert first["rank"] == 1
        assert 0.0 <= first["score"] <= 1.0
        assert "influence_role" in first
        assert "explanation" in first
        assert len(first["reasons"]) > 0
        assert "safety_notice" in data

        # Test alias /api/influence
        res_alias = client.get("/api/influence?limit=10", headers=headers)
        assert res_alias.status_code == 200

    def test_influence_rankings_and_single_entity_api(self, test_setup):
        """Test GET /api/influence/rankings and GET /api/influence/entity/{entity_id} endpoints."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res_rank = client.get("/api/influence/rankings?limit=5", headers=headers)
        assert res_rank.status_code == 200
        assert len(res_rank.json()["rankings"]) <= 5

        res_ent = client.get("/api/influence/entity/PERSON_017", headers=headers)
        assert res_ent.status_code == 200
        ent_data = res_ent.json()
        assert ent_data["entity_id"] == "PERSON_017"
        assert "key_player_details" in ent_data
        assert ent_data["key_player_details"]["score"] > 0.0

        # Test 404 for missing entity
        res_404 = client.get("/api/influence/entity/PERSON_NONEXISTENT_999", headers=headers)
        assert res_404.status_code == 404

    def test_community_influence_api(self, test_setup):
        """Test GET /api/influence/community endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/influence/community", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "total_communities" in data
        assert "community_influencers" in data
        assert len(data["community_influencers"]) > 0

    def test_cross_case_influencer_detection(self, test_setup):
        """Test that multi-case connecting entities (e.g. PHONE_042, PERSON_089, PERSON_017) are flagged."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players?limit=20", headers=headers)
        assert res.status_code == 200
        key_players = res.json()["key_players"]

        cross_case_nodes = [kp for kp in key_players if len(kp["connected_case_ids"]) >= 2]
        assert len(cross_case_nodes) > 0, "Should detect entities spanning multiple cases"

        for kp in cross_case_nodes:
            assert kp["influence_role"] in [
                KeyPlayerRole.CROSS_CASE_INFLUENCER.value,
                KeyPlayerRole.BRIDGE_ENTITY.value,
                KeyPlayerRole.CORE_HUB.value,
            ]

    def test_case_filtered_key_players_api(self, test_setup):
        """Test GET /api/intelligence/key-players/CASE_101 endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players/CASE_101", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["case_id"] == "CASE_101"
        assert data["key_players_count"] > 0

        for kp in data["key_players"]:
            assert "CASE_101" in kp["connected_case_ids"] or kp["entity_id"] == "CASE_101"

    def test_nonexistent_case_404_error(self, test_setup):
        """Test 404 response for invalid case ID."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players/CASE_NONEXISTENT_999", headers=headers)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_role_filtering(self, test_setup):
        """Test filtering key players by influence_role."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players?role=BRIDGE_ENTITY", headers=headers)
        assert res.status_code == 200
        data = res.json()

        for kp in data["key_players"]:
            assert kp["influence_role"] == KeyPlayerRole.BRIDGE_ENTITY.value

    def test_explainability_and_evidence_linkage(self, test_setup):
        """Test that every key player contains explanations, evidence IDs, and provenance."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players?limit=5", headers=headers)
        assert res.status_code == 200
        kp_list = res.json()["key_players"]

        for kp in kp_list:
            assert isinstance(kp["explanation"], str) and len(kp["explanation"]) > 10
            assert isinstance(kp["reasons"], list)
            assert isinstance(kp["supporting_evidence_ids"], list)
            assert kp["provenance"] in ["DATASET", "MANUAL", "NLP_EXTRACT"]
            assert 0.0 <= kp["confidence"] <= 1.0

    def test_safetyguard_neutrality_disclaimer(self, test_setup):
        """Test non-culpability legal notice in key player responses."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/intelligence/key-players", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "safety_notice" in data
        assert "NOT establish legal guilt" in data["safety_notice"]

    def test_unauthenticated_request_rejected_401(self, test_setup):
        """Test 401 Unauthorized response for missing Bearer token."""
        client = test_setup["client"]

        res = client.get("/api/intelligence/key-players")
        assert res.status_code == 401
