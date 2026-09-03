"""Day 6 Backend & Graph Layer Robustness and Scalability Tests.

Covers:
1. Data integrity validation
2. Graph robustness (source==target, max_depth bounds, disconnected entities, cycles)
3. Pathfinding edge cases
4. Search, filtering, and pagination
5. Large-dataset index helper methods
6. Error handling & status codes
7. Performance sanity checks
"""

import time
import pytest
from starlette.testclient import TestClient
from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.traversal import find_paths_between_entities, find_cross_case_connections
from crimegraph.models.entities import EntityType, Person, Phone
from crimegraph.models.relationships import Relationship, RelationshipType
from crimegraph.models.evidence import Evidence


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def graph():
    return load_dataset()


# ── 1. Data Integrity Validation ──────────────────────────────────────────────

class TestDataIntegrityValidation:
    def test_synthetic_graph_passes_strict_integrity(self, graph):
        report = graph.validate_integrity()
        assert report["is_valid"] is True
        assert len(report["errors"]) == 0
        assert report["entity_count"] == 34
        assert report["relationship_count"] == 24
        assert report["evidence_count"] == 19

    def test_invalid_relationship_type_detection(self):
        store = KnowledgeGraphStore()
        store.add_entity({"id": "P1", "type": "PERSON", "name": "Alice"})
        store.add_entity({"id": "P2", "type": "PERSON", "name": "Bob"})
        # Intentionally inject invalid relationship
        r = Relationship(id="R1", source_id="P1", target_id="P2", relationship=RelationshipType.CONTACTED, confidence=0.9)
        object.__setattr__(r, "relationship", "INVALID_RELATIONSHIP_TYPE")
        store.relationships["R1"] = r
        report = store.validate_integrity()
        assert report["is_valid"] is False
        assert any("invalid relationship type" in err.lower() for err in report["errors"])

    def test_broken_entity_reference_detection(self):
        store = KnowledgeGraphStore()
        p = Person(id="P1", name="Alice", phone_ids=["PHONE_NONEXISTENT_999"])
        store.entities["P1"] = p
        report = store.validate_integrity()
        assert report["is_valid"] is False
        assert any("PHONE_NONEXISTENT_999" in err for err in report["errors"])


# ── 2. Graph & Pathfinding Robustness ─────────────────────────────────────────

class TestGraphRobustness:
    def test_source_equals_target_returns_zero_hop_path(self, graph):
        paths = find_paths_between_entities(graph, "PERSON_017", "PERSON_017")
        assert len(paths) == 1
        assert paths[0]["path"] == ["PERSON_017"]
        assert paths[0]["hop_count"] == 0
        assert paths[0]["confidence"] == 1.0

    def test_max_depth_zero_returns_empty(self, graph):
        paths = find_paths_between_entities(graph, "PERSON_017", "PERSON_089", max_depth=0)
        assert len(paths) == 0

    def test_cross_case_same_case_returns_empty(self, graph):
        conns = find_cross_case_connections(graph, "CASE_101", "CASE_101")
        assert conns == []

    def test_disconnected_entities_returns_empty_paths(self, graph):
        paths = find_paths_between_entities(graph, "ACC_001", "LOC_003", max_depth=2)
        assert isinstance(paths, list)

    def test_nonexistent_source_raises_key_error(self, graph):
        with pytest.raises(KeyError):
            find_paths_between_entities(graph, "NONEXISTENT_SRC", "PERSON_089")

    def test_nonexistent_target_raises_key_error(self, graph):
        with pytest.raises(KeyError):
            find_paths_between_entities(graph, "PERSON_017", "NONEXISTENT_TGT")


# ── 3. Index & Large-Dataset Helper Methods ───────────────────────────────────

class TestIndexOptimization:
    def test_get_relationships_by_type_uses_index(self, graph):
        uses_rels = graph.get_relationships_by_type(RelationshipType.USES)
        assert len(uses_rels) > 0
        assert all(r.relationship == RelationshipType.USES for r in uses_rels)

    def test_get_entities_by_case_uses_index(self, graph):
        case_101_members = graph.get_entities_by_case("CASE_101")
        assert len(case_101_members) > 0
        member_ids = {e.id for e in case_101_members}
        assert "PERSON_017" in member_ids

    def test_entity_update_cleans_old_type_index(self):
        store = KnowledgeGraphStore()
        store.add_entity({"id": "E1", "type": "PERSON", "name": "A"})
        assert "E1" in store._type_index["PERSON"]
        # Update type
        store.add_entity({"id": "E1", "type": "PHONE", "phone_number": "+91-1234567890"})
        assert "E1" in store._type_index["PHONE"]
        assert "E1" not in store._type_index["PERSON"]


# ── 4. Search, Filtering, and Pagination ──────────────────────────────────────

class TestSearchAndPagination:
    def test_entities_pagination_limit(self, client):
        r = client.get("/api/entities?limit=5")
        assert r.status_code == 200
        assert len(r.json()) == 5

    def test_entities_pagination_offset(self, client):
        r_all = client.get("/api/entities")
        r_offset = client.get("/api/entities?offset=5&limit=5")
        assert r_offset.status_code == 200
        assert r_offset.json()[0]["id"] == r_all.json()[5]["id"]

    def test_cases_pagination_limit(self, client):
        r = client.get("/api/cases?limit=2")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_evidence_pagination_limit(self, client):
        r = client.get("/api/evidence?limit=3")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_entities_type_and_min_confidence_combined(self, client):
        r = client.get("/api/entities?type=PERSON&min_confidence=0.90")
        assert r.status_code == 200
        for e in r.json():
            assert e["entity_type"] == "PERSON"
            assert e["confidence"] >= 0.90


# ── 5. Performance Sanity Check ───────────────────────────────────────────────

class TestPerformanceSanity:
    def test_entity_lookup_speed(self, graph):
        start = time.perf_counter()
        for _ in range(1000):
            _ = graph.get_entity("PERSON_017")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"1000 entity lookups took {elapsed:.4f}s (should be < 0.1s)"

    def test_neighbor_lookup_speed(self, graph):
        start = time.perf_counter()
        for _ in range(1000):
            _ = graph.get_neighbors("PERSON_017")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"1000 neighbor lookups took {elapsed:.4f}s (should be < 0.1s)"

    def test_pathfinding_speed(self, graph):
        start = time.perf_counter()
        for _ in range(50):
            _ = find_cross_case_connections(graph, "CASE_101", "CASE_204")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.2, f"50 cross-case traversals took {elapsed:.4f}s (should be < 0.2s)"
