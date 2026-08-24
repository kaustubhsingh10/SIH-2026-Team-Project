"""API Contract & Endpoint Test Suite for CrimeGraph AI."""

import pytest
from fastapi.testclient import TestClient
from crimegraph.api.app import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CrimeGraph AI Backend API"
    assert data["status"] == "operational"


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_get_case_graph_endpoint():
    response = client.get("/api/cases/CASE_101/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0


def test_get_entity_details_endpoint():
    response = client.get("/api/entities/PERSON_017")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "PERSON_017"
    assert "relationships" in data
    assert "evidence" in data


def test_get_case_connections_endpoint():
    response = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
    assert response.status_code == 200
    data = response.json()
    assert "connections" in data
    assert len(data["connections"]) > 0
    conn = data["connections"][0]
    assert conn["case_a"] == "CASE_101"
    assert conn["case_b"] == "CASE_204"
    assert conn["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]


def test_get_case_timeline_endpoint():
    response = client.get("/api/cases/CASE_101/timeline")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert len(data["events"]) > 0


def test_get_evidence_endpoint():
    response = client.get("/api/evidence/EVID_042_01")
    assert response.status_code == 200
    data = response.json()
    assert data["evidence_id"] == "EVID_042_01"
    assert "source_text" in data
