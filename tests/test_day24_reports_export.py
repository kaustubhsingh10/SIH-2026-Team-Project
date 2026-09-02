"""Day 24 Three-Way Integration Test Suite for CrimeGraph AI.

Verifies complete end-to-end integration across:
1. Kaustubh — Backend Report Generator & Data Layer
2. Shruti — Frontend Reports UI & Export Controls
3. Aditya — AI Investigator & Grounded Intelligence Layer

Tests all 11 final acceptance criteria specified in Day 24 specification.
"""

import json
import pytest
from fastapi.testclient import TestClient
from crimegraph.api.app import app
from crimegraph.data.loader import load_dataset
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.ai.investigator import AIInvestigator
from crimegraph.reports.reporter import InvestigationReporter


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def graph_store():
    return load_dataset()


def test_01_backend_report_generation_grounded(graph_store):
    """Kaustubh Backend: Report generator extracts grounded data from KnowledgeGraphStore."""
    reporter = InvestigationReporter(graph_store)
    report = reporter.generate_report("CASE_101")

    assert report["case_id"] == "CASE_101"
    assert report["status"] == "generated"
    assert "report_id" in report
    assert "timestamp" in report
    assert "title" in report
    assert "executive_summary" in report
    assert len(report["key_entities"]) > 0
    assert len(report["relationships"]) > 0
    assert len(report["timeline_events"]) > 0
    assert len(report["suspicious_patterns"]) > 0
    assert "network_intelligence" in report
    assert len(report["evidence"]) > 0
    assert len(report["source_provenance"]) > 0
    assert "safety_disclaimer" in report
    assert "content" in report
    assert "LEGAL & SAFETY DISCLAIMER" in report["content"]


def test_02_canonical_path_preservation(client):
    """Three-Way: Canonical path CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204 preserved in report."""
    response = client.post("/api/reports", json={"case_id": "CASE_101"})
    assert response.status_code == 200
    data = response.json()

    entity_ids = [e["id"] for e in data["key_entities"]]
    assert "PERSON_017" in entity_ids
    assert "PHONE_042" in entity_ids

    # Check cross-case patterns for PERSON_089 and the exact 5-node canonical path linking CASE_101 to CASE_204
    patterns = data["suspicious_patterns"]
    c204_bridges = [p for p in patterns if "CASE_204" in p.get("cases", [])]
    assert len(c204_bridges) > 0
    bridge_path = c204_bridges[0]["path"]
    assert bridge_path == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
    assert "PERSON_089" in bridge_path


def test_03_export_formats_and_integrity(client):
    """Kaustubh & Shruti: JSON, PDF, and Markdown exports generate valid non-leaking attachments."""
    # 1. JSON Export
    res_json = client.post("/api/reports/export", json={"case_id": "CASE_101", "format": "json"})
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    assert "crimegraph_report_CASE_101.json" in res_json.headers["content-disposition"]
    json_data = res_json.json()
    assert json_data["case_id"] == "CASE_101"

    # Verify no credentials/tokens/internal paths
    json_str = json.dumps(json_data)
    assert "password" not in json_str.lower()
    assert "secret" not in json_str.lower()
    assert "bearer" not in json_str.lower()
    assert "C:\\Users\\" not in json_str

    # 2. PDF Export
    res_pdf = client.post("/api/reports/export", json={"case_id": "CASE_101", "format": "pdf"})
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert res_pdf.content.startswith(b"%PDF-1.4")
    assert "crimegraph_report_CASE_101.pdf" in res_pdf.headers["content-disposition"]

    # 3. Markdown Export
    res_md = client.post("/api/reports/export", json={"case_id": "CASE_101", "format": "markdown"})
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "CRIMEGRAPH AI" in res_md.text


def test_04_ai_investigator_report_integration(graph_store):
    """Aditya AI: Investigator query output is grounded and incorporates AI insights."""
    investigator = AIInvestigator(graph_store)
    res = investigator.query("How are Case 101 and Case 204 connected?")

    assert res["query_type"] == "CROSS_CASE_CONNECTION"
    assert res["confidence"] >= 0.90
    assert res["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
    assert "PHONE_042" in res["shared_entities"]
    assert len(res["evidence"]) > 0
    assert res["explanation"] is not None
    assert res["investigative_lead"] is not None
    assert "disclaimer" in res


def test_05_safety_refusal_preservation(client):
    """Aditya & SafetyGuard: Guilt queries trigger SAFETY_REFUSAL with confidence 0.0."""
    guilt_queries = [
        "Is Person 017 guilty?",
        "Who is the culprit in Case 101?",
        "Did Aarav Verma commit the crime?"
    ]
    for q in guilt_queries:
        res = client.post("/api/investigate", json={"question": q})
        assert res.status_code == 200
        data = res.json()
        assert data["query_type"] == "SAFETY_REFUSAL"
        assert data["confidence"] == 0.0
        assert data["path"] == []
        assert "does not determine guilt" in data["answer"].lower()
        assert "disclaimer" in data


def test_06_security_auth_rbac_boundaries(client):
    """Kaustubh & Auth: 401 unauthenticated and 403 unauthorized case access."""
    # 1. Unauthenticated bearer token fails with 401
    res_401 = client.get("/api/cases", headers={"Authorization": "Bearer invalid_token_123"})
    assert res_401.status_code == 401

    # 2. Restricted officer accessing unauthorized case returns 403
    login_res = client.post("/api/auth/login", json={"username": "RESTRICTED_OFFICER", "password": "password123"})
    assert login_res.status_code == 200
    restricted_token = login_res.json()["access_token"]

    res_403 = client.post(
        "/api/reports",
        json={"case_id": "CASE_204"},
        headers={"Authorization": f"Bearer {restricted_token}"}
    )
    assert res_403.status_code == 403


def test_07_edge_cases_and_error_handling(client):
    """Three-Way: 404 for invalid case, graceful fallback for unknown entity."""
    # 404 Nonexistent Case
    res_404 = client.post("/api/reports", json={"case_id": "CASE_999"})
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()

    # NOT_FOUND for unknown entity AI query
    res_nf = client.post("/api/investigate", json={"question": "What relationships does Person 999 have?"})
    assert res_nf.status_code == 200
    assert res_nf.json()["query_type"] == "NOT_FOUND"
    assert res_nf.json()["confidence"] == 0.0
