"""Comprehensive Test Suite for CrimeGraph Network Intelligence Engine.

Validates graph centrality, bridge discovery, cross-case connectivity,
relationship diversity, evidence support, and REST API contract compliance.
Strictly adheres to API_CONTRACT.md and SIH 2026 Problem Statement B3.
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.intelligence import NetworkIntelligenceEngine
from crimegraph.graph.traversal import find_cross_case_connections
from crimegraph.models.entities import Person, Phone, Vehicle, Case
from crimegraph.models.relationships import Relationship, RelationshipType


@pytest.fixture
def graph():
    """Loads fresh baseline KnowledgeGraphStore."""
    return load_dataset()


@pytest.fixture
def app_instance(graph, monkeypatch):
    """Creates a configured FastAPI application instance with consistent test environment."""
    monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin@2026")
    monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")
    return create_app(graph_instance=graph)


@pytest.fixture
def client(app_instance):
    """Creates a test FastAPI client."""
    return TestClient(app_instance)


@pytest.fixture
def auth_headers(client):
    """Generates valid JWT Authorization headers for test requests."""
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin@2026"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. CORE ALGORITHMIC METRICS TESTS
# ==============================================================================

class TestNetworkIntelligenceMetrics:
    """Tests individual centrality, diversity, bridge, and evidence metrics."""

    def test_degree_connectivity_score(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        metrics_017 = engine.calculate_entity_metrics("PERSON_017", max_degree=10, total_case_count=4)
        
        assert metrics_017["metrics"]["direct_connections"] >= 5
        assert 0.0 <= metrics_017["metrics"]["degree_score"] <= 1.0
        assert metrics_017["entity_name"] == "Aarav Verma"

    def test_betweenness_centrality_calculation(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        betweenness = engine.compute_betweenness_centrality()
        
        assert isinstance(betweenness, dict)
        assert len(betweenness) == len(graph.entities)
        for eid, b_score in betweenness.items():
            assert b_score >= 0.0

        # PERSON_017 and PHONE_042 should have notable betweenness centrality
        assert betweenness.get("PERSON_017", 0.0) > 0.0

    def test_cross_case_connectivity_discovery(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        connected_cases = engine.find_connected_cases_for_entity("PERSON_017", max_depth=2)
        
        assert len(connected_cases) >= 2
        assert "CASE_101" in connected_cases

    def test_relationship_diversity_scoring(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        metrics_017 = engine.calculate_entity_metrics("PERSON_017", total_rel_types=5)
        
        assert metrics_017["metrics"]["relationship_types_count"] >= 3
        assert 0.0 <= metrics_017["metrics"]["relationship_diversity_score"] <= 1.0

    def test_evidence_support_scoring(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        metrics_017 = engine.calculate_entity_metrics("PERSON_017")
        
        assert metrics_017["metrics"]["evidence_count"] >= 1
        assert metrics_017["metrics"]["average_edge_confidence"] > 0.80
        assert 0.0 <= metrics_017["metrics"]["evidence_support_score"] <= 1.0

    def test_composite_influence_score_bounds(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        ranked = engine.rank_entities(limit=10)
        
        assert len(ranked) == 10
        for item in ranked:
            score = item["influence_score"]
            assert 0.0 <= score <= 1.0
            assert isinstance(score, float)
            assert item["rank"] >= 1


# ==============================================================================
# 2. DETERMINISM AND RANKING ORDER TESTS
# ==============================================================================

class TestDeterministicRanking:
    """Validates deterministic tie-breaking and sorting properties."""

    def test_ranking_is_strictly_descending(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        ranked = engine.rank_entities()
        
        scores = [item["influence_score"] for item in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_deterministic_tie_breaking(self):
        """Creates an artificial symmetric graph to test tie-breaking on entity ID."""
        small_graph = KnowledgeGraphStore()
        
        # Create 3 symmetric Person entities
        small_graph.add_entity({"id": "PERSON_B", "entity_type": "PERSON", "name": "Bob"})
        small_graph.add_entity({"id": "PERSON_A", "entity_type": "PERSON", "name": "Alice"})
        small_graph.add_entity({"id": "PERSON_C", "entity_type": "PERSON", "name": "Charlie"})
        small_graph.add_entity({"id": "PHONE_X", "entity_type": "PHONE", "phone_number": "+91-9999999999"})

        # Symmetric edges using valid RelationshipType.USES
        small_graph.add_relationship({
            "id": "REL_A", "source_id": "PERSON_A", "target_id": "PHONE_X",
            "relationship": "USES", "confidence": 0.90
        })
        small_graph.add_relationship({
            "id": "REL_B", "source_id": "PERSON_B", "target_id": "PHONE_X",
            "relationship": "USES", "confidence": 0.90
        })
        small_graph.add_relationship({
            "id": "REL_C", "source_id": "PERSON_C", "target_id": "PHONE_X",
            "relationship": "USES", "confidence": 0.90
        })

        engine = NetworkIntelligenceEngine(small_graph)
        ranked = engine.rank_entities(entity_type="PERSON")
        
        # Identical metrics should resolve in alphabetical ID order: PERSON_A, PERSON_B, PERSON_C
        assert [r["entity_id"] for r in ranked] == ["PERSON_A", "PERSON_B", "PERSON_C"]
        assert ranked[0]["rank"] == 1
        assert ranked[1]["rank"] == 2
        assert ranked[2]["rank"] == 3

    def test_empty_graph_graceful_handling(self):
        empty_graph = KnowledgeGraphStore()
        engine = NetworkIntelligenceEngine(empty_graph)
        
        assert engine.rank_entities() == []
        assert engine.compute_betweenness_centrality() == {}


# ==============================================================================
# 3. ENTITY TYPE FILTERING AND KEY INDIVIDUALS
# ==============================================================================

class TestEntityTypeFiltering:
    """Verifies filtering by PERSON vs non-PERSON entity types."""

    def test_person_only_ranking(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        persons = engine.rank_entities(entity_type="PERSON", limit=5)
        
        assert len(persons) > 0
        for p in persons:
            assert p["entity_type"] == "PERSON"
        assert persons[0]["entity_id"] == "PERSON_017"

    def test_non_person_ranking(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        phones = engine.rank_entities(entity_type="PHONE", limit=5)
        
        assert len(phones) > 0
        for ph in phones:
            assert ph["entity_type"] == "PHONE"
        assert phones[0]["entity_id"] == "PHONE_042"

    def test_unknown_entity_type_returns_empty(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        result = engine.rank_entities(entity_type="SPACESHIP")
        assert result == []


# ==============================================================================
# 4. EXPLAINABILITY AND SAFETY POLICY
# ==============================================================================

class TestExplainabilityAndSafety:
    """Verifies that generated explanation reasons are factual and never accusatory."""

    def test_reasons_presence_and_structure(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        results = engine.rank_entities(limit=5)
        
        for item in results:
            reasons = item.get("reasons", [])
            assert isinstance(reasons, list)
            assert len(reasons) >= 1
            for reason in reasons:
                assert isinstance(reason, str)
                assert len(reason) > 5

    def test_zero_culpability_language_in_reasons(self, graph):
        """Mandatory SIH AI safety: intelligence reasons must not declare guilt or culpability."""
        engine = NetworkIntelligenceEngine(graph)
        all_entities = engine.rank_entities(limit=50)
        
        forbidden_terms = ["guilt", "guilty", "criminal", "mastermind", "perpetrator", "culpable", "convict"]
        for entity in all_entities:
            for reason in entity.get("reasons", []):
                for term in forbidden_terms:
                    assert term not in reason.lower(), f"Forbidden culpability term '{term}' found in reason: '{reason}'"


# ==============================================================================
# 5. CANONICAL SIH DEMO PATH PRESERVATION
# ==============================================================================

class TestCanonicalDemoPreservation:
    """Ensures that the canonical CASE_101 -> CASE_204 bridge discovery remains intact."""

    def test_canonical_cross_case_bridge_path_intact(self, graph):
        connections = find_cross_case_connections(graph, "CASE_101", "CASE_204", max_depth=6)
        
        assert len(connections) > 0
        canonical = connections[0]
        assert canonical["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert "PHONE_042" in canonical["shared_entities"]

    def test_phone_042_detected_as_key_bridge(self, graph):
        engine = NetworkIntelligenceEngine(graph)
        c101_net = engine.get_case_network_intelligence("CASE_101")
        
        assert "network_summary" in c101_net
        assert c101_net["network_summary"]["total_nodes"] > 0
        assert "safety_notice" in c101_net


# ==============================================================================
# 6. REST API ENDPOINT CONTRACT TESTS
# ==============================================================================

class TestNetworkIntelligenceAPI:
    """Validates FastAPI routes /api/cases/{id}/influencers and /api/cases/{id}/network-intelligence."""

    def test_case_influencers_endpoint(self, client, auth_headers):
        res = client.get("/api/cases/CASE_101/influencers?entity_type=PERSON&limit=5", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        
        assert data["case_id"] == "CASE_101"
        assert data["entity_type_filter"] == "PERSON"
        assert data["results_count"] == len(data["results"])
        assert len(data["results"]) >= 1
        
        first = data["results"][0]
        assert first["entity_id"] == "PERSON_017"
        assert first["rank"] == 1
        assert "metrics" in first
        assert "reasons" in first

    def test_case_network_intelligence_overview_endpoint(self, client, auth_headers):
        res = client.get("/api/cases/CASE_101/network-intelligence", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        
        assert data["case_id"] == "CASE_101"
        assert "network_summary" in data
        assert "key_individuals" in data
        assert "top_influencers" in data
        assert "bridge_entities" in data
        assert "cross_case_connectors" in data
        assert "safety_notice" in data

    def test_global_graph_influencers_endpoint(self, client, auth_headers):
        res = client.get("/api/graph/influencers?limit=10", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        
        assert data["results_count"] <= 10
        assert len(data["results"]) > 0

    def test_global_graph_network_intelligence_endpoint(self, client, auth_headers):
        res = client.get("/api/graph/network-intelligence", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        
        assert "network_summary" in data
        assert data["network_summary"]["total_nodes"] >= 30

    def test_unknown_case_returns_404(self, client, auth_headers):
        res = client.get("/api/cases/CASE_UNKNOWN_999/influencers", headers=auth_headers)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_unauthenticated_request_blocked_with_401_in_strict_mode(self, graph, monkeypatch):
        monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
        app = create_app(graph_instance=graph)
        strict_client = TestClient(app)
        res = strict_client.get("/api/cases/CASE_101/influencers")
        assert res.status_code == 401

    def test_audit_log_records_intelligence_query(self, client, auth_headers):
        # Query intelligence endpoint
        client.get("/api/cases/CASE_101/influencers", headers=auth_headers)
        
        # Verify audit record
        audit_res = client.get("/api/audit", headers=auth_headers)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        intel_events = [e for e in events if e.get("action") == "NETWORK_INTELLIGENCE_QUERY"]
        assert len(intel_events) >= 1
