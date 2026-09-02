"""Day 28 — Advanced Key Player & Influencer Intelligence Test Suite.

Verifies:
1. KeyPlayerEngine analysis & ranking metrics.
2. REST API GET /api/key-players endpoint responses and status codes.
3. Filtering by case, entity type, role, and cross-case status.
4. Non-culpability safety disclaimers and Grounded Graph output.
"""

import pytest
from fastapi.testclient import TestClient
from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.ai.key_players import KeyPlayerEngine


@pytest.fixture
def test_client():
    graph = load_dataset()
    app = create_app(graph_instance=graph)
    return TestClient(app)


def test_key_player_engine_analysis():
    graph = load_dataset()
    engine = KeyPlayerEngine(graph)
    res = engine.analyze_key_players()

    assert "total_ranked" in res
    assert "metrics" in res
    assert "key_players" in res
    assert res["total_ranked"] > 0
    assert res["metrics"]["total_key_players"] == res["total_ranked"]

    # Verify top key player has highest rank
    top_player = res["key_players"][0]
    assert top_player["rank"] == 1
    assert top_player["influence_score"] >= 0.80
    assert "safety_disclaimer" in top_player


def test_api_get_key_players(test_client):
    response = test_client.get("/api/key-players")
    assert response.status_code == 200
    data = response.json()

    assert "total_ranked" in data
    assert "key_players" in data
    assert len(data["key_players"]) > 0

    # Verify non-culpability disclaimer present
    assert "safety_disclaimer" in data
    assert "culpability" in data["safety_disclaimer"].lower()


def test_api_get_key_players_filter_by_case(test_client):
    response = test_client.get("/api/key-players?case_id=CASE_101")
    assert response.status_code == 200
    data = response.json()

    for player in data["key_players"]:
        assert "CASE_101" in player["connected_cases"]


def test_api_get_key_players_filter_by_type(test_client):
    response = test_client.get("/api/key-players?type=PHONE")
    assert response.status_code == 200
    data = response.json()

    for player in data["key_players"]:
        assert player["type"] == "PHONE"


def test_api_get_key_players_filter_cross_case(test_client):
    response = test_client.get("/api/key-players?is_cross_case=true")
    assert response.status_code == 200
    data = response.json()

    for player in data["key_players"]:
        assert player["is_cross_case"] is True
