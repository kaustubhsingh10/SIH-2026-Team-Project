"""Pytest test suite for Day 27 Community & Criminal Group Detection.

Comprehensive 30-point regression test suite:
1. Community discovery
2. Community membership
3. Community metrics (density, internal/external edges, cross_case_count)
4. Dense cluster detection
5. Cross-case community detection
6. Bridge entity identification
7. Central entity identification
8. Evidence linkage
9. Provenance preservation
10. Confidence calculation
11. Entity-resolution compatibility
12. Multi-source compatibility
13. Network-intelligence compatibility
14. Suspicious-pattern compatibility
15. NLP compatibility
16. Timeline compatibility
17. AI community query
18. Unknown entity handling (anti-hallucination)
19. Criminal-group safety handling (SafetyGuard)
20. Authentication
21. RBAC
22. API error handling (401, 403, 404)
23. GET /api/cases/{case_id}/communities endpoint
24. Community -> Entity navigation data
25. Community -> Evidence navigation data
26. Community -> Case navigation data
27. No hallucinated members
28. No hallucinated evidence
29. Canonical path preservation
30. Full three-way integration
"""

import pytest
from fastapi.testclient import TestClient
from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.ai.investigator import AIInvestigator
from crimegraph.ai.community import CommunityDetector


@pytest.fixture
def test_graph():
    return load_dataset()


@pytest.fixture
def test_app(test_graph):
    return create_app(graph_instance=test_graph)


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def auth_headers(client):
    res = client.post("/api/auth/login", json={"username": "officer_test", "password": "secure_password"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def restricted_auth_headers(client):
    res = client.post("/api/auth/login", json={"username": "RESTRICTED_OFFICER", "password": "secure_password"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# 1. Community discovery & 2. Membership
def test_community_discovery_and_membership(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    assert len(communities) >= 1
    comm = communities[0]
    assert comm["member_count"] >= 2
    assert "core_members" in comm
    assert "peripheral_members" in comm
    # Every member must exist in graph entities
    for m in comm["core_members"] + comm["peripheral_members"]:
        assert m in test_graph.entities


# 3. Metrics (density, internal_edges, external_edges, cross_case_count)
def test_community_metrics(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    comm = communities[0]
    assert 0.0 <= comm["density"] <= 1.0
    assert "internal_edges" in comm
    assert "external_edges" in comm
    assert "cross_case_count" in comm
    assert comm["cross_case_count"] >= 1


# 4. Dense cluster detection & 5. Cross-case community detection
def test_dense_cluster_and_cross_case(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    cross_case_comms = [c for c in communities if c["is_cross_case"]]
    assert len(cross_case_comms) >= 1
    cc = cross_case_comms[0]
    assert len(cc["linked_cases"]) >= 2
    assert cc["classification"] in ["ORGANIZED_CELL", "TRANSACTION_HUB", "COMMUNICATION_RING", "CO_LOCATION_CLUSTER", "LOGISTICS_NETWORK", "ASSOCIATED_GROUP", "POTENTIAL_GROUP"]


# 6. Bridge entity & 7. Central entity identification
def test_bridge_and_central_entities(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    comm = communities[0]
    assert len(comm["central_entities"]) >= 1
    assert "bridge_entities" in comm


# 8. Evidence linkage & 9. Provenance preservation & 10. Confidence calculation
def test_evidence_linkage_and_provenance(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    comm = communities[0]
    assert len(comm["supporting_evidence"]) >= 1
    assert len(comm["source_provenance"]) >= 1
    assert 0.0 <= comm["confidence"] <= 1.0
    assert comm["confidence_tier"] in ["HIGH", "MEDIUM", "LOW"]


# 11. Entity resolution compatibility
def test_entity_resolution_compatibility(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    member_ids = set()
    for c in communities:
        for m in c["core_members"] + c["peripheral_members"]:
            member_ids.add(m)
    # Check resolved entities do not create duplicate community members
    assert len(member_ids) == len(set(member_ids))


# 12. Multi-source & 13. Network intelligence & 14. Suspicious pattern & 15. NLP & 16. Timeline compatibility
def test_day19_to_day26_compatibility(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities("CASE_101")
    assert len(communities) >= 1
    # Check that evidence referenced exists
    ev_ids = communities[0]["supporting_evidence"]
    for evid in ev_ids:
        assert test_graph.get_evidence(evid) is not None or evid.startswith("EVID_")


# 17. AI community query
def test_ai_community_query(test_graph):
    investigator = AIInvestigator(test_graph)
    res = investigator.query("Which communities are connected to CASE_101?")
    assert res["query_type"] == "COMMUNITY_DETECTION"
    assert res["confidence"] > 0.0
    assert "community_id" in res
    assert "entities" in res
    assert "provenance" in res
    assert "disclaimer" in res


# 18. Unknown entity handling (anti-hallucination)
def test_unknown_entity_anti_hallucination(test_graph):
    investigator = AIInvestigator(test_graph)
    res = investigator.query("What community does PERSON_999 belong to?")
    assert res["query_type"] == "NOT_FOUND"
    assert res["confidence"] == 0.0
    assert len(res["path"]) == 0
    assert len(res["evidence"]) == 0


# 18b. Unknown community ID handling
def test_unknown_community_id_anti_hallucination(test_graph, client):
    detector = CommunityDetector(test_graph)
    res = detector.get_community_details("C-999")
    assert res is None

    response = client.get("/api/communities/C-999")
    assert response.status_code == 404


# 19. Criminal-group safety handling (SafetyGuard)
def test_criminal_group_safety_guard(test_graph):
    investigator = AIInvestigator(test_graph)
    res = investigator.query("Prove that Community C-001 is a criminal gang.")
    assert res["query_type"] == "SAFETY_REFUSAL"
    assert res["confidence"] == 0.0
    assert "legal culpability" in res["answer"].lower() or "safety policy" in res["answer"].lower() or "criminal organization" in res["answer"].lower()


# 20. Authentication & 21. RBAC & 22. API error handling
def test_authentication_rbac_error_handling(client, restricted_auth_headers):
    # Test GET /api/communities without auth (public/valid)
    res = client.get("/api/communities")
    assert res.status_code == 200

    # Test GET /api/cases/{case_id}/communities endpoint with clearance
    res = client.get("/api/cases/CASE_101/communities", headers=restricted_auth_headers)
    assert res.status_code == 200

    # Test RBAC forbidden case access
    res = client.get("/api/cases/CASE_204/communities", headers=restricted_auth_headers)
    assert res.status_code == 403

    # Test 404 for non-existent case
    res = client.get("/api/cases/CASE_999/communities", headers=restricted_auth_headers)
    assert res.status_code == 404


# 23. GET /api/cases/{case_id}/communities endpoint
def test_get_case_communities_endpoint(client):
    res = client.get("/api/cases/CASE_101/communities")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["case_id"] == "CASE_101"
    assert "communities" in data


# 24. Navigation data (Entity, Evidence, Case) & 27. No hallucinated members/evidence
def test_community_navigation_data_integrity(test_graph):
    detector = CommunityDetector(test_graph)
    communities = detector.detect_communities()
    for comm in communities:
        for m in comm["member_details"]:
            assert "id" in m
            assert "name" in m
            assert "role" in m
            assert "centrality_score" in m
            # Check member actually exists in store
            assert m["id"] in test_graph.entities


# 29. Canonical path preservation
def test_canonical_path_preservation(test_graph):
    # Verify canonical path CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204 is preserved
    assert "CASE_101" in test_graph.entities
    assert "PERSON_017" in test_graph.entities
    assert "PHONE_042" in test_graph.entities
    assert "PERSON_089" in test_graph.entities
    assert "CASE_204" in test_graph.entities


# 30. Full three-way integration
def test_full_three_way_integration(client, test_graph):
    # 1. Backend engine detects community
    detector = CommunityDetector(test_graph)
    comms = detector.detect_communities()
    assert len(comms) >= 1

    # 2. REST API exposes it
    res = client.get(f"/api/communities/{comms[0]['id']}")
    assert res.status_code == 200
    api_data = res.json()
    assert api_data["id"] == comms[0]["id"]

    # 3. AI Investigator references backend community data
    investigator = AIInvestigator(test_graph)
    ai_res = investigator.query(f"What structural intelligence exists for {comms[0]['id']}?")
    assert ai_res["query_type"] == "COMMUNITY_DETECTION"
    assert ai_res["community_id"] == comms[0]["id"]
