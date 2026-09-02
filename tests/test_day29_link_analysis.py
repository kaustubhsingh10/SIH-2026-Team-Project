"""Day 29 Unit and Integration Tests for Advanced Link Analysis & Path Discovery.

Tests pathfinding traversal, cross-case connection discovery, max depth limits, and REST API routes.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.data.loader import load_dataset
from crimegraph.graph.traversal import find_paths_between_entities
from crimegraph.api.app import create_app


@pytest.fixture
def graph():
    return load_dataset()


@pytest.fixture
def client(graph):
    app = create_app(graph_instance=graph)
    return TestClient(app)


def test_pathfinding_canonical_cross_case_path(graph):
    """Test multi-hop path discovery between CASE_101 and CASE_204."""
    paths = find_paths_between_entities(graph, "CASE_101", "CASE_204", max_depth=6)
    assert len(paths) > 0

    primary = paths[0]
    assert primary["source_id"] == "CASE_101"
    assert primary["target_id"] == "CASE_204"
    assert "PHONE_042" in primary["shared_entities"]
    assert primary["confidence"] >= 0.90
    assert primary["hop_count"] >= 3
    assert len(primary["steps"]) == primary["hop_count"]


def test_pathfinding_entity_to_entity_path(graph):
    """Test path discovery between PERSON_017 and PERSON_089."""
    paths = find_paths_between_entities(graph, "PERSON_017", "PERSON_089", max_depth=6)
    assert len(paths) > 0

    p = paths[0]
    assert "PHONE_042" in p["path"]
    assert p["confidence"] >= 0.90


def test_pathfinding_nonexistent_target_raises_keyerror(graph):
    """Test KeyError raised for unknown entities."""
    with pytest.raises(KeyError):
        find_paths_between_entities(graph, "CASE_101", "NONEXISTENT_ENTITY_999")


def test_api_get_paths_success(client):
    """Test GET /api/paths REST API endpoint."""
    response = client.get("/api/paths?source_id=CASE_101&target_id=CASE_204&max_depth=6")
    assert response.status_code == 200
    data = response.json()
    assert data["source_id"] == "CASE_101"
    assert data["target_id"] == "CASE_204"
    assert data["path_count"] > 0
    assert len(data["paths"]) > 0

    first_path = data["paths"][0]
    assert "steps" in first_path
    assert "confidence" in first_path


def test_api_get_paths_404_for_unknown_source(client):
    """Test GET /api/paths returns 404 for non-existent source entity."""
    response = client.get("/api/paths?source_id=UNKNOWN_999&target_id=CASE_204")
    assert response.status_code == 404
