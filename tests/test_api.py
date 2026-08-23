"""API Contract & Endpoint Test Suite for CrimeGraph AI."""

import pytest
from fastapi.testclient import TestClient
from crimegraph.api import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "CrimeGraph AI"
    assert "disclaimer" in data


def test_extract_endpoint():
    payload = {
        "document_id": "DOC_TEST_001",
        "text": "Aarav Verma (PERSON_017) was observed using vehicle MH-01-AB-1234 and phone +91-9876543210."
    }
    response = client.post("/api/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "DOC_TEST_001"
    assert len(data["entities"]) >= 1
    assert len(data["evidence"]) >= 1


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


def test_post_reports_endpoint():
    payload = {"case_id": "CASE_101"}
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"
    assert "report_id" in data
    assert "content" in data
    assert "LEGAL & SAFETY DISCLAIMER" in data["content"]


def test_get_pending_entity_resolutions_endpoint():
    response = client.get("/api/entity-resolution/pending")
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert len(data["candidates"]) > 0


def test_investigate_endpoint():
    payload = {"question": "Find connections between Case 101 and Case 204"}
    response = client.post("/api/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query_type"] == "CROSS_CASE_CONNECTION"
    assert "CASE_101" in data["answer"]
    assert "disclaimer" in data
