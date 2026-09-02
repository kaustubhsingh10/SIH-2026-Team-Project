"""Pytest test suite for Day 26 Advanced Entity Resolution & Identity Linking.

Tests:
1. GET /api/entity-resolution/pending endpoint returns candidates with full fields, confidence tiers, provenance, and conflict flags.
2. GET /api/entity-resolution/compare endpoint performs side-by-side attribute comparison between two entities.
3. AIInvestigator handles resolution queries with structured output (confirmed_links, probable_links, unresolved_candidates, conflicting_claims).
"""

import pytest
from fastapi.testclient import TestClient
from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset
from crimegraph.ai.resolution import EntityResolver
from crimegraph.ai.investigator import AIInvestigator


@pytest.fixture
def test_app():
    graph_store = load_dataset()
    app = create_app(graph_instance=graph_store)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_get_pending_entity_resolutions(client):
    response = client.get("/api/entity-resolution/pending")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "PENDING_REVIEW"
    assert data["candidate_count"] >= 1
    assert "candidates" in data

    cand = data["candidates"][0]
    assert "id" in cand
    assert "entity_a" in cand
    assert "entity_b" in cand
    assert "similarity" in cand
    assert "confidence_tier" in cand
    assert "match_status" in cand
    assert "matching_fields" in cand
    assert "source_provenance" in cand
    assert "explanation" in cand


def test_compare_entities_endpoint(client):
    response = client.get("/api/entity-resolution/compare?entity_a=PERSON_017&entity_b=PERSON_092")
    assert response.status_code == 200
    data = response.json()

    assert data["entity_a"]["id"] == "PERSON_017"
    assert data["entity_b"]["id"] == "PERSON_092"
    assert data["similarity"] >= 0.70
    assert "confidence_tier" in data
    assert "match_status" in data
    assert len(data["matching_fields"]) >= 1
    assert "source_provenance" in data


def test_ai_investigator_identity_resolution():
    graph_store = load_dataset()
    investigator = AIInvestigator(graph_store)

    res = investigator.query("Perform identity resolution and compare candidate records for Aarav Verma")
    assert res["query_type"] == "IDENTITY_RESOLUTION"
    assert res["confidence"] >= 0.90
    assert "confirmed_links" in res
    assert "probable_links" in res
    assert "unresolved_candidates" in res
    assert "conflicting_claims" in res
    assert len(res["confirmed_links"]) >= 1
    assert len(res["probable_links"]) >= 1
