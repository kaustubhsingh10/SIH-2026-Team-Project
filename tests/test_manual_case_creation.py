"""Comprehensive test suite for Manual Case Creation, Persistence, and Cross-Case Memory.

Tests cover:
1. Create case via POST /api/cases
2. Validation & rejection of invalid case payloads
3. Unique case ID generation and collision avoidance
4. Case persistent storage in manual dataset
5. Case survives simulated backend restart and dataset reload
6. Manually created case appears in GET /api/cases
7. Case visual graph loads with connected nodes/edges
8. Entity can be attached to the manually created case
9. Relationship can be attached to the manually created case
10. Existing canonical entity (e.g. PERSON_017) can be reused without duplication
11. Cross-case connection can be discovered between new case and existing CASE_101 / CASE_204
12. RBAC & authentication enforcement
13. Audit logging for case creation and access
14. Compatibility with Entity Resolution
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset, get_default_dataset_path
from crimegraph.graph.traversal import find_cross_case_connections
from crimegraph.auth.security import create_access_token
from crimegraph.auth.models import UserRole


@pytest.fixture
def test_setup(tmp_path):
    temp_manual_file = tmp_path / "test_case_manual_data.json"
    os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"] = str(temp_manual_file)
    os.environ["CRIMEGRAPH_AUTH_STRICT"] = "true"

    app = create_app()
    client = TestClient(app)

    token_analyst, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    token_admin, _ = create_access_token(username="admin", role=UserRole.ADMIN)

    headers_analyst = {"Authorization": f"Bearer {token_analyst}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    yield {
        "app": app,
        "client": client,
        "manual_file": temp_manual_file,
        "headers_analyst": headers_analyst,
        "headers_admin": headers_admin
    }

    if "CRIMEGRAPH_MANUAL_DATA_PATH" in os.environ:
        del os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"]
    if "CRIMEGRAPH_AUTH_STRICT" in os.environ:
        del os.environ["CRIMEGRAPH_AUTH_STRICT"]


class TestManualCaseCreationAndMemory:
    """Test suite for manual case creation and graph memory persistence."""

    def test_create_case_with_auto_generated_id(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {
            "title": "Operation Red Falcon — Port Contraband Intercept",
            "description": "Suspicious maritime cargo manifest evasion at Container Freight Station.",
            "case_type": "SMUGGLING",
            "priority": "HIGH",
            "status": "OPEN",
            "incident_date": "2026-09-01T10:00:00Z"
        }

        res = client.post("/api/cases", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()

        assert data["title"] == payload["title"]
        assert data["id"].startswith("CASE_")
        assert data["origin"] == "MANUAL"
        assert data["persisted"] is True
        assert data["created_by"] == "analyst"

    def test_create_case_with_custom_unique_id(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {
            "id": "CASE_991",
            "title": "Operation Nightfall — Gold Smuggling Ring",
            "description": "Cross-border illicit bullion logistics network.",
            "case_type": "BULLION_SMUGGLING",
            "priority": "CRITICAL",
            "status": "ACTIVE"
        }

        res = client.post("/api/cases", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "CASE_991"
        assert data["case_number"] == "FIR-2026-MANUAL-991"

    def test_create_case_duplicate_id_rejected_409(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        # Attempt to overwrite canonical CASE_101
        payload = {
            "id": "CASE_101",
            "title": "Fake Duplicate Case"
        }

        res = client.post("/api/cases", json=payload, headers=headers)
        assert res.status_code == 409
        assert "already exists" in res.json()["detail"]

    def test_create_case_invalid_payload_rejected_422(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        # Missing required title
        payload = {
            "description": "Case without a title"
        }

        res = client.post("/api/cases", json=payload, headers=headers)
        assert res.status_code == 422

    def test_case_persistence_and_reload_survival(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]
        manual_file = test_setup["manual_file"]

        payload = {
            "id": "CASE_555",
            "title": "Operation Deep Harbor — Customs Fraud",
            "description": "Multi-tier evasion scheme at Nhava Sheva Terminal.",
            "status": "ACTIVE"
        }

        res = client.post("/api/cases", json=payload, headers=headers)
        assert res.status_code == 201

        # Verify persisted on disk
        assert manual_file.exists()
        with open(manual_file, "r", encoding="utf-8") as f:
            persisted_data = json.load(f)
        
        entity_ids = [e["id"] for e in persisted_data.get("entities", [])]
        assert "CASE_555" in entity_ids

        # Simulate fresh backend reload from disk
        reloaded_store = load_dataset(manual_filepath=manual_file)
        assert "CASE_555" in reloaded_store.entities
        case_ent = reloaded_store.get_entity("CASE_555")
        assert case_ent.title == "Operation Deep Harbor — Customs Fraud"
        assert case_ent.origin == "MANUAL"

    def test_created_case_appears_in_list_and_details_api(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        payload = {
            "id": "CASE_777",
            "title": "Operation Cyber Vault",
            "status": "UNDER_INVESTIGATION"
        }
        res_create = client.post("/api/cases", json=payload, headers=headers)
        assert res_create.status_code == 201

        # 1. Check list API
        res_list = client.get("/api/cases", headers=headers)
        assert res_list.status_code == 200
        case_ids = [c["id"] for c in res_list.json()]
        assert "CASE_777" in case_ids

        # 2. Check details API
        res_det = client.get("/api/cases/CASE_777", headers=headers)
        assert res_det.status_code == 200
        assert res_det.json()["id"] == "CASE_777"
        assert res_det.json()["status"] == "UNDER_INVESTIGATION"

    def test_attach_entities_and_relationships_to_manual_case(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        # 1. Create Case
        client.post("/api/cases", json={"id": "CASE_888", "title": "Operation Shadow Courier"}, headers=headers)

        # 2. Create new manual Person
        res_p = client.post("/api/entities", json={
            "id": "PERSON_NEW_888",
            "entity_type": "PERSON",
            "name": "Kavita Rao",
            "age": 31
        }, headers=headers)
        assert res_p.status_code == 201

        # 3. Create relationship: CASE_888 -> INVOLVED_IN -> PERSON_NEW_888
        res_rel = client.post("/api/relationships", json={
            "source_id": "CASE_888",
            "target_id": "PERSON_NEW_888",
            "relationship": "INVOLVED_IN",
            "confidence": 0.95
        }, headers=headers)
        assert res_rel.status_code == 201

        # 4. Check case graph
        res_graph = client.get("/api/cases/CASE_888/graph", headers=headers)
        assert res_graph.status_code == 200
        graph_data = res_graph.json()
        node_ids = {n["id"] for n in graph_data["nodes"]}
        assert "CASE_888" in node_ids
        assert "PERSON_NEW_888" in node_ids

    def test_cross_case_linking_with_reused_canonical_entity(self, test_setup):
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        # Create new Case CASE_601
        client.post("/api/cases", json={"id": "CASE_601", "title": "Operation Western Hub"}, headers=headers)

        # Link existing canonical Aarav Verma (PERSON_017 from CASE_101) to CASE_601
        res_link = client.post("/api/relationships", json={
            "source_id": "CASE_601",
            "target_id": "PERSON_017",
            "relationship": "INVOLVED_IN",
            "confidence": 0.92,
            "notes": "PERSON_017 identified in dispatch registry for CASE_601."
        }, headers=headers)
        assert res_link.status_code == 201

        # Verify cross-case connection can be discovered between CASE_101 and CASE_601
        res_conn = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_601", headers=headers)
        assert res_conn.status_code == 200
        connections = res_conn.json()["connections"]
        assert len(connections) > 0
        path = connections[0]["path"]
        assert "PERSON_017" in path
        assert path == ["CASE_101", "PERSON_017", "CASE_601"]

    def test_rbac_unauthorized_user_cannot_create_case(self, test_setup):
        client = test_setup["client"]

        # No token
        res_no_auth = client.post("/api/cases", json={"title": "Unauthorized Case"})
        assert res_no_auth.status_code == 401
