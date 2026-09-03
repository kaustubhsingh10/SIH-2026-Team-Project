"""Day 7 Backend & Graph Layer Reliability, Data Consistency, and Hardening Tests.

Covers:
1. Data consistency & structural metrics
2. Case timeline chronological retrieval
3. Subgraph memoization & cache invalidation
4. Reversed cross-case connection symmetry (CASE_204 -> CASE_101)
5. Entity resolution referential integrity (only real graph entities)
6. Neighbor direction query validation
7. API validation & error handling
8. Main demonstration regression & safety
"""

import pytest
from starlette.testclient import TestClient
from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.traversal import find_cross_case_connections
from crimegraph.models.entities import EntityType


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def graph():
    return load_dataset()


# ── 1. Data Consistency & Structural Metrics ──────────────────────────────────

class TestDataConsistencyAndMetrics:
    def test_graph_store_stats_accuracy(self, graph):
        stats = graph.get_stats()
        assert stats["total_entities"] == 34
        assert stats["total_relationships"] == 24
        assert stats["total_evidence"] == 19
        assert "PERSON" in stats["entity_types"]
        assert "CASE" in stats["entity_types"]
        assert stats["entity_types"]["CASE"] >= 2
        assert stats["entity_types"]["PERSON"] >= 3
        assert "High" in stats["evidence_tiers"]

    def test_case_timeline_chronological_order(self, client):
        r = client.get("/api/cases/CASE_101/timeline")
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        events = data["events"]
        assert isinstance(events, list)
        assert len(events) >= 1
        # Check timestamps are sorted ascending
        timestamps = [e.get("timestamp") for e in events if e.get("timestamp")]
        assert timestamps == sorted(timestamps)

    def test_timeline_nonexistent_case_returns_404(self, client):
        r = client.get("/api/cases/CASE_NONEXISTENT_999/timeline")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()


# ── 2. Graph Subgraph Memoization & Caching ───────────────────────────────────

class TestSubgraphCaching:
    def test_subgraph_memoization_cache(self, graph):
        # First call populates cache
        subgraph_1 = graph.get_case_subgraph("CASE_101")
        assert "CASE_101" in graph._subgraph_cache
        # Second call hits cache
        subgraph_2 = graph.get_case_subgraph("CASE_101")
        assert subgraph_1 is subgraph_2

    def test_cache_invalidates_on_new_entity(self, graph):
        _ = graph.get_case_subgraph("CASE_101")
        assert "CASE_101" in graph._subgraph_cache
        # Add new entity
        graph.add_entity({"id": "TEMP_TEST_ENTITY", "type": "PERSON", "name": "Temp Test"})
        assert len(graph._subgraph_cache) == 0


# ── 3. Cross-Case Connection Symmetry & Robustness ────────────────────────────

class TestCrossCaseConnections:
    def test_forward_cross_case_connection(self, graph):
        conns = find_cross_case_connections(graph, "CASE_101", "CASE_204")
        assert len(conns) >= 1
        path = conns[0]["path"]
        assert path == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert conns[0]["shared_entities"] == ["PHONE_042"]

    def test_reverse_cross_case_connection_symmetry(self, graph):
        conns = find_cross_case_connections(graph, "CASE_204", "CASE_101")
        assert len(conns) >= 1
        path = conns[0]["path"]
        assert path == ["CASE_204", "PERSON_089", "PHONE_042", "PERSON_017", "CASE_101"]
        assert conns[0]["shared_entities"] == ["PHONE_042"]
        assert conns[0]["confidence"] == 0.93

    def test_same_case_connection_via_api(self, client):
        r = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_101")
        assert r.status_code == 200
        assert r.json()["connections"] == []

    def test_nonexistent_case_connections_returns_404(self, client):
        r = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_999")
        assert r.status_code == 404
        assert "CASE_999" in r.json()["detail"]


# ── 4. Entity Resolution Referential Integrity ────────────────────────────────

class TestEntityResolutionIntegrity:
    def test_pending_resolution_references_real_entities(self, client, graph):
        r = client.get("/api/entity-resolution/pending")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "PENDING_REVIEW"
        candidates = data["candidates"]
        for cand in candidates:
            # Verify both entity IDs genuinely exist in the knowledge graph
            assert cand["entity_a"] in graph.entities
            assert cand["entity_b"] in graph.entities
            assert 0.0 <= cand["similarity"] <= 1.0


# ── 5. Neighbor Direction Query Validation ────────────────────────────────────

class TestNeighborDirectionValidation:
    def test_neighbor_direction_outgoing(self, client):
        r = client.get("/api/entities/PERSON_017/neighbors?direction=outgoing")
        assert r.status_code == 200
        assert "neighbors" in r.json()

    def test_neighbor_direction_incoming(self, client):
        r = client.get("/api/entities/PERSON_017/neighbors?direction=incoming")
        assert r.status_code == 200
        assert "neighbors" in r.json()

    def test_neighbor_invalid_direction_returns_422(self, client):
        r = client.get("/api/entities/PERSON_017/neighbors?direction=INVALID_DIRECTION")
        assert r.status_code == 422


# ── 6. Case Entities Endpoint Filtering ───────────────────────────────────────

class TestCaseEntitiesFiltering:
    def test_case_entities_type_filter(self, client):
        r = client.get("/api/cases/CASE_101/entities?entity_type=PERSON")
        assert r.status_code == 200
        nodes = r.json()
        assert len(nodes) >= 1
        assert all(n["entity_type"] == "PERSON" for n in nodes)

    def test_case_entities_nonexistent_case_returns_404(self, client):
        r = client.get("/api/cases/CASE_NONEXISTENT/entities")
        assert r.status_code == 404
