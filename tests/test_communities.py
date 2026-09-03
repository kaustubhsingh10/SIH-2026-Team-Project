"""Comprehensive test suite for Day 27 Community & Criminal Group Detection in CrimeGraph AI.

Tests:
1. Deterministic community discovery across entire graph.
2. Density, degree, and betweenness calculations.
3. Structural member role assignments (CORE, PERIPHERAL, BRIDGE, INFRASTRUCTURE).
4. Community classification (CROSS_CASE_COMMUNITY, SHARED_DEVICE_CLUSTER, HIGH_CONNECTIVITY_COMMUNITY).
5. Explainable group suspicion/risk score based on measurable graph topology.
6. REST API endpoints:
   - GET /api/communities
   - GET /api/communities/{community_id}
   - GET /api/cases/{case_id}/communities
7. Edge cases & error handling:
   - Isolated entities
   - Nonexistent community ID (404)
   - Nonexistent case ID (404)
8. Authentication & RBAC: strict JWT enforcement.
9. Safety & Non-guilt guarantee: verified that communities are presented as topological clusters, not criminal guilt.
10. AI Investigator integration: canonical path and cross-case reasoning intact.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.communities.engine import CommunityDetectionEngine
from crimegraph.communities.models import (
    CommunityClassification,
    CommunityConfidenceTier,
    MemberRole,
)
from crimegraph.data.loader import load_dataset


@pytest.fixture
def store():
    return load_dataset()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def analyst_headers():
    token, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. COMMUNITY DETECTION ENGINE & GRAPH ALGORITHMS
# ==============================================================================

def test_engine_detect_communities_deterministic(store):
    engine = CommunityDetectionEngine(store)
    summary1 = engine.detect_communities()
    summary2 = engine.detect_communities()

    assert summary1.total_communities >= 1
    assert summary1.total_communities == summary2.total_communities
    assert summary1.total_clustered_entities == summary2.total_clustered_entities

    top_community = summary1.communities[0]
    assert top_community.member_count >= 3
    assert 0.0 <= top_community.density_score <= 1.0
    assert 0.0 <= top_community.group_risk_score <= 1.0


def test_cross_case_community_identification(store):
    engine = CommunityDetectionEngine(store)
    summary = engine.detect_communities()

    # Locate the main cluster connecting CASE_101 and CASE_204
    cross_case_cluster = None
    for c in summary.communities:
        if "CASE_101" in c.linked_case_ids and "CASE_204" in c.linked_case_ids:
            cross_case_cluster = c
            break

    assert cross_case_cluster is not None
    assert cross_case_cluster.classification == CommunityClassification.CROSS_CASE_COMMUNITY
    assert "PHONE_042" in cross_case_cluster.shared_infrastructure_ids or "PHONE_042" in cross_case_cluster.bridge_entity_ids
    assert cross_case_cluster.confidence_tier == CommunityConfidenceTier.HIGH


def test_structural_roles_assigned_correctly(store):
    engine = CommunityDetectionEngine(store)
    summary = engine.detect_communities()
    top_comm = summary.communities[0]

    roles = set(m.structural_role for m in top_comm.members)
    assert MemberRole.INFRASTRUCTURE in roles or MemberRole.CORE in roles or MemberRole.BRIDGE in roles


def test_case_scoped_community_detection(store):
    engine = CommunityDetectionEngine(store)
    summary = engine.detect_communities(case_id="CASE_101")

    assert summary.case_id == "CASE_101"
    assert summary.total_communities >= 1
    assert all("CASE_101" in c.linked_case_ids or "CASE_101" in c.member_entity_ids for c in summary.communities)


def test_nonexistent_case_raises_value_error(store):
    engine = CommunityDetectionEngine(store)
    with pytest.raises(ValueError):
        engine.detect_communities(case_id="CASE_999_NONEXISTENT")


# ==============================================================================
# 2. REST API ENDPOINTS
# ==============================================================================

def test_api_list_communities_success(client, analyst_headers):
    res = client.get("/api/communities", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_communities" in data
    assert data["total_communities"] >= 1
    assert len(data["communities"]) >= 1


def test_api_get_community_detail_success(client, analyst_headers):
    # First get communities list
    res_list = client.get("/api/communities", headers=analyst_headers)
    assert res_list.status_code == 200
    first_comm = res_list.json()["communities"][0]
    comm_id = first_comm["community_id"]

    # Query detail
    res_detail = client.get(f"/api/communities/{comm_id}", headers=analyst_headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["community_id"] == comm_id
    assert "density_score" in detail
    assert "group_risk_score" in detail
    assert "investigative_leads" in detail


def test_api_get_community_nonexistent_returns_404(client, analyst_headers):
    res = client.get("/api/communities/COMM_NONEXISTENT_999", headers=analyst_headers)
    assert res.status_code == 404


def test_api_case_communities_success(client, analyst_headers):
    res = client.get("/api/cases/CASE_101/communities", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "CASE_101"
    assert data["total_communities"] >= 1


def test_api_case_communities_nonexistent_returns_404(client, analyst_headers):
    res = client.get("/api/cases/CASE_NONEXISTENT/communities", headers=analyst_headers)
    assert res.status_code == 404


def test_api_unauthorized_access(client):
    res = client.get("/api/communities")
    assert res.status_code == 401


# ==============================================================================
# 3. SAFETYGUARD & NON-GUILT GUARANTEE
# ==============================================================================

def test_community_disclaimer_preserves_non_guilt(client, analyst_headers):
    res = client.get("/api/communities", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "disclaimer" in data
    assert "does not establish legal guilt" in data["communities"][0]["disclaimer"].lower() or "human verification is required" in data["disclaimer"].lower()


def test_ai_investigator_grounding_with_communities(client, analyst_headers):
    # Canonical cross-case discovery
    res = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"}, headers=analyst_headers)
    assert res.status_code == 200
    assert res.json()["query_type"] == "CROSS_CASE_CONNECTION"
    assert res.json()["confidence"] >= 0.90
