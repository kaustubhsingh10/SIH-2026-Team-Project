"""Day 30 Unit & Integration Tests for AI Pattern & Anomaly Intelligence.

Tests pattern detection endpoints, 7 pattern categories, anomaly scores, and filtering.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.data.loader import load_dataset
from crimegraph.api.app import create_app


@pytest.fixture
def graph():
    return load_dataset()


@pytest.fixture
def client(graph):
    app = create_app(graph_instance=graph)
    return TestClient(app)


def test_patterns_endpoint_all_categories(client):
    """Test GET /api/patterns returns patterns spanning 7 core categories."""
    response = client.get("/api/patterns")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "patterns" in data
    assert data["count"] >= 7

    types = {p["pattern_type"] for p in data["patterns"]}
    expected = {
        "CROSS_CASE_BRIDGE",
        "HIGH_CONNECTIVITY_HUB",
        "TEMPORAL_CLUSTER",
        "REPEATED_CONTACT_PATTERN",
        "ENTITY_ACTIVITY_ANOMALY",
        "MULTI_SOURCE_CORROBORATION",
        "UNUSUAL_PATH_PATTERN"
    }
    assert expected.issubset(types)


def test_patterns_schema_and_explainability(client):
    """Test every pattern contains anomaly score, observed data, computed pattern, and non-culpability disclaimer."""
    response = client.get("/api/patterns")
    assert response.status_code == 200
    patterns = response.json()["patterns"]

    for p in patterns:
        assert "pattern_id" in p
        assert "title" in p
        assert "pattern_type" in p
        assert "confidence" in p
        assert "anomaly_score" in p
        assert 0.0 <= p["anomaly_score"] <= 1.0
        assert "severity" in p
        assert "observed_data" in p
        assert "computed_pattern" in p
        assert "investigative_lead" in p
        assert "disclaimer" in p
        assert "guilt" not in p["disclaimer"].lower() or "does not" in p["disclaimer"].lower()


def test_patterns_filtering_by_case(client):
    """Test filtering patterns by case_id."""
    response = client.get("/api/patterns?case_id=CASE_101")
    assert response.status_code == 200
    patterns = response.json()["patterns"]
    assert len(patterns) > 0
    for p in patterns:
        assert "CASE_101" in p["cases"] or "ALL" in p["cases"]


def test_patterns_filtering_by_type(client):
    """Test filtering patterns by pattern_type."""
    response = client.get("/api/patterns?pattern_type=HIGH_CONNECTIVITY_HUB")
    assert response.status_code == 200
    patterns = response.json()["patterns"]
    assert len(patterns) > 0
    for p in patterns:
        assert p["pattern_type"] == "HIGH_CONNECTIVITY_HUB"


def test_patterns_filtering_by_min_confidence(client):
    """Test filtering patterns by minimum confidence."""
    response = client.get("/api/patterns?min_confidence=0.95")
    assert response.status_code == 200
    patterns = response.json()["patterns"]
    for p in patterns:
        assert p["confidence"] >= 0.95
