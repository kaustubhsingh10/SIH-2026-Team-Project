"""Tests for AI Investigator Backend Data Access.

Verifies:
1. Retrieval of an existing case and its connected entities (suspects, vehicles, phones, accounts, locations).
2. Retrieval of relationships and evidence.
3. Retrieval of manually created entities linked to cases.
4. Unified retrieval of dataset + manual entities together.
5. Nonexistent case handling without crashing (clean 404).
6. Entity context retrieval and keyword search for AI reasoning.
7. Security verification (no secrets/leakage).
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app


@pytest.fixture
def client(tmp_path):
    temp_manual_file = tmp_path / "test_manual_data.json"
    os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"] = str(temp_manual_file)
    
    app = create_app()
    client_instance = TestClient(app)
    yield client_instance

    if "CRIMEGRAPH_MANUAL_DATA_PATH" in os.environ:
        del os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"]


class TestAICaseContextRetrieval:
    """Verifies targeted case context retrieval for AI models."""

    def test_retrieve_existing_case_context(self, client):
        res = client.get("/api/investigate/context/cases/CASE_101")
        assert res.status_code == 200
        data = res.json()
        assert data["case"]["id"] == "CASE_101"
        assert "summary" in data
        assert "entities" in data
        assert "relationships" in data
        assert "evidence" in data

    def test_case_context_connected_persons_and_suspects(self, client):
        res = client.get("/api/investigate/context/cases/CASE_101")
        assert res.status_code == 200
        data = res.json()
        person_ids = [p["id"] for p in data["entities"]["persons"]]
        assert "PERSON_017" in person_ids

    def test_case_context_connected_vehicles(self, client):
        res = client.get("/api/investigate/context/cases/CASE_101")
        assert res.status_code == 200
        data = res.json()
        vehicle_ids = [v["id"] for v in data["entities"]["vehicles"]]
        assert len(vehicle_ids) > 0
        assert "VEHICLE_017" in vehicle_ids

    def test_case_context_connected_phones(self, client):
        res = client.get("/api/investigate/context/cases/CASE_101")
        assert res.status_code == 200
        data = res.json()
        phone_ids = [ph["id"] for ph in data["entities"]["phones"]]
        assert "PHONE_042" in phone_ids

    def test_case_context_connected_accounts(self, client):
        res = client.get("/api/investigate/context/cases/CASE_204")
        assert res.status_code == 200
        data = res.json()
        account_ids = [acc["id"] for acc in data["entities"]["accounts"]]
        assert len(account_ids) > 0
        assert "ACC_002" in account_ids

    def test_case_context_relationships_and_evidence(self, client):
        res = client.get("/api/investigate/context/cases/CASE_101")
        assert res.status_code == 200
        data = res.json()
        assert len(data["relationships"]) > 0
        assert len(data["evidence"]) > 0
        ev_ids = [ev["evidence_id"] for ev in data["evidence"]]
        assert "EVID_101_01" in ev_ids

    def test_case_context_includes_manual_entities(self, client):
        # 1. Create manual person
        p_res = client.post("/api/entities", json={
            "entity_type": "PERSON",
            "name": "Manish Gupta",
            "description": "Logistics Informant"
        })
        assert p_res.status_code == 201
        manual_p_id = p_res.json()["id"]

        # 2. Link manual person to CASE_101
        rel_res = client.post("/api/relationships", json={
            "source_id": manual_p_id,
            "target_id": "CASE_101",
            "relationship": "INVOLVED_IN",
            "confidence": 0.94
        })
        assert rel_res.status_code == 201

        # 3. Retrieve CASE_101 AI context
        context_res = client.get("/api/investigate/context/cases/CASE_101")
        assert context_res.status_code == 200
        context_data = context_res.json()

        # 4. Verify manual entity appears in both persons and manual_entities
        person_ids = [p["id"] for p in context_data["entities"]["persons"]]
        manual_ids = [m["id"] for m in context_data["entities"]["manual_entities"]]
        assert manual_p_id in person_ids
        assert manual_p_id in manual_ids
        assert context_data["summary"]["manual_entities_count"] >= 1

    def test_nonexistent_case_returns_404_cleanly(self, client):
        res = client.get("/api/investigate/context/cases/CASE_99999")
        assert res.status_code == 404
        assert "CASE_99999" in res.json()["detail"]


class TestAIEntityContextAndSearch:
    """Verifies targeted entity context and search for AI reasoning."""

    def test_entity_context_neighborhood(self, client):
        res = client.get("/api/investigate/context/entities/PERSON_017")
        assert res.status_code == 200
        data = res.json()
        assert data["entity"]["id"] == "PERSON_017"
        assert "CASE_101" in data["linked_cases"]
        assert len(data["connected_entities"]) > 0
        assert len(data["relationships"]) > 0

    def test_nonexistent_entity_returns_404_cleanly(self, client):
        res = client.get("/api/investigate/context/entities/NONEXISTENT_XYZ")
        assert res.status_code == 404

    def test_ai_context_search_by_name(self, client):
        res = client.post("/api/investigate/context/search", json={
            "query": "Aarav Verma"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["results_count"] >= 1
        entity_names = [e.get("name") for e in data["entities"]]
        assert "Aarav Verma" in entity_names

    def test_ai_context_search_by_phone(self, client):
        res = client.post("/api/investigate/context/search", json={
            "query": "+91-9876543210"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["results_count"] >= 1
        assert any(e.get("phone_number") == "+91-9876543210" for e in data["entities"])

    def test_ai_context_search_manual_entity(self, client):
        # Create unique manual entity
        client.post("/api/entities", json={
            "entity_type": "ORGANIZATION",
            "name": "Syndicate Gold Vaults LLC",
            "address": "Opera House, Mumbai"
        })

        res = client.post("/api/investigate/context/search", json={
            "query": "Syndicate Gold Vaults"
        })
        assert res.status_code == 200
        data = res.json()
        assert any(e.get("name") == "Syndicate Gold Vaults LLC" for e in data["entities"])


class TestAISecurityAndIntegrity:
    """Verifies that AI context endpoints do not leak secrets or private data."""

    def test_no_secrets_in_case_context(self, client):
        res = client.get("/api/investigate/context/cases/CASE_101")
        text = res.text
        assert "api_key" not in text.lower()
        assert "secret" not in text.lower()
        assert "CRIMEGRAPH_DATA_PATH" not in text
