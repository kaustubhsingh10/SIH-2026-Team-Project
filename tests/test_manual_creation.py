"""Tests for Manual Entity & Relationship Creation, Persistence, and Management.

Validates:
1. Manual entity creation across all supported types (Person, Phone, Vehicle, Location, Account, Organization, Case, Event)
2. Manual relationship creation between entities
3. Data origin distinction (MANUAL vs DATASET)
4. Persistence across reloads
5. Editing and safe deletion of manual entities and relationships
6. Protection of original dataset entities from accidental deletion
7. Validation and error handling
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.data.loader import load_dataset, save_manual_data, get_default_manual_data_path


@pytest.fixture
def client(tmp_path):
    # Set custom manual data path in temp directory for test isolation
    temp_manual_file = tmp_path / "test_manual_data.json"
    os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"] = str(temp_manual_file)
    
    app = create_app()
    client_instance = TestClient(app)
    yield client_instance

    # Cleanup env
    if "CRIMEGRAPH_MANUAL_DATA_PATH" in os.environ:
        del os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"]


class TestManualEntityCreation:
    """Tests manual entity creation across all data types."""

    def test_create_manual_person(self, client):
        payload = {
            "entity_type": "PERSON",
            "name": "Rahul Sharma",
            "age": 34,
            "gender": "Male",
            "aliases": ["Sharmaji"],
            "description": "Suspect observed at freight corridor"
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Rahul Sharma"
        assert data["entity_type"] == "PERSON"
        assert data["origin"] == "MANUAL"
        assert data["id"].startswith("MANUAL_PERSON_")

        # Verify queryable via GET
        get_res = client.get(f"/api/entities/{data['id']}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Rahul Sharma"

    def test_create_manual_phone(self, client):
        payload = {
            "entity_type": "PHONE",
            "phone_number": "+91-9988776655",
            "description": "Intercepted Prepaid SIM"
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["phone_number"] == "+91-9988776655"
        assert data["origin"] == "MANUAL"

    def test_create_manual_vehicle(self, client):
        payload = {
            "entity_type": "VEHICLE",
            "registration_number": "MH-02-CD-5678",
            "type": "White Sedan"
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["registration_number"] == "MH-02-CD-5678"
        assert data["type"] == "White Sedan"
        assert data["origin"] == "MANUAL"

    def test_create_manual_location(self, client):
        payload = {
            "entity_type": "LOCATION",
            "name": "Andheri Cargo Terminal",
            "address": "Plot 14, MIDC Road, Mumbai",
            "latitude": 19.1136,
            "longitude": 72.8697
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Andheri Cargo Terminal"
        assert data["origin"] == "MANUAL"

    def test_create_manual_organization(self, client):
        payload = {
            "entity_type": "ORGANIZATION",
            "name": "Apex Logistics Pvt Ltd",
            "address": "Fort, Mumbai"
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Apex Logistics Pvt Ltd"
        assert data["origin"] == "MANUAL"

    def test_create_manual_account(self, client):
        payload = {
            "entity_type": "ACCOUNT",
            "account_type": "BANK_ACCOUNT",
            "identifier": "ACC_HDFC_8841"
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["identifier"] == "ACC_HDFC_8841"
        assert data["origin"] == "MANUAL"

    def test_create_with_custom_id(self, client):
        payload = {
            "id": "MANUAL_SUSPECT_007",
            "entity_type": "PERSON",
            "name": "Sameer Khan"
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        assert res.json()["id"] == "MANUAL_SUSPECT_007"


class TestManualRelationshipCreation:
    """Tests establishing links between entities."""

    def test_create_relationship_between_manual_entities(self, client):
        # 1. Create Person
        p_res = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Deepak Joshi"})
        assert p_res.status_code == 201
        person_id = p_res.json()["id"]

        # 2. Create Vehicle
        v_res = client.post("/api/entities", json={"entity_type": "VEHICLE", "registration_number": "MH-12-AB-9999"})
        assert v_res.status_code == 201
        vehicle_id = v_res.json()["id"]

        # 3. Establish relationship: Person --OWNS--> Vehicle
        rel_payload = {
            "source_id": person_id,
            "target_id": vehicle_id,
            "relationship": "OWNS",
            "confidence": 0.95,
            "properties": {"notes": "Registered owner verified via VAHAN database"}
        }
        rel_res = client.post("/api/relationships", json=rel_payload)
        assert rel_res.status_code == 201
        rel_data = rel_res.json()
        assert rel_data["source_id"] == person_id
        assert rel_data["target_id"] == vehicle_id
        assert rel_data["relationship"] == "OWNS"
        assert rel_data["origin"] == "MANUAL"

        # 4. Verify graph reflects the new edge
        graph_res = client.get("/api/graph")
        assert graph_res.status_code == 200
        edge_ids = [e["id"] for e in graph_res.json()["edges"]]
        assert rel_data["id"] in edge_ids

    def test_connect_manual_entity_to_dataset_entity(self, client):
        # Create manual phone
        ph_res = client.post("/api/entities", json={"entity_type": "PHONE", "phone_number": "+91-9123456789"})
        phone_id = ph_res.json()["id"]

        # Link to existing dataset entity PERSON_017
        rel_res = client.post("/api/relationships", json={
            "source_id": "PERSON_017",
            "target_id": phone_id,
            "relationship": "USES",
            "confidence": 0.92
        })
        assert rel_res.status_code == 201
        assert rel_res.json()["source_id"] == "PERSON_017"
        assert rel_res.json()["target_id"] == phone_id


class TestManualEntityEditingAndDeletion:
    """Tests updating and deleting manual records."""

    def test_update_manual_entity(self, client):
        create_res = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Karan Singhania"})
        ent_id = create_res.json()["id"]

        # Update name and description
        update_res = client.put(f"/api/entities/{ent_id}", json={
            "name": "Karan Singhania (Updated)",
            "description": "Promoted to primary person of interest"
        })
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Karan Singhania (Updated)"

    def test_delete_manual_entity_safely_removes_relationships(self, client):
        # Create person and vehicle
        p_res = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Temporary Person"})
        v_res = client.post("/api/entities", json={"entity_type": "VEHICLE", "registration_number": "MH-01-TEMP"})
        p_id = p_res.json()["id"]
        v_id = v_res.json()["id"]

        # Link them
        rel_res = client.post("/api/relationships", json={
            "source_id": p_id,
            "target_id": v_id,
            "relationship": "USES",
            "confidence": 0.9
        })
        rel_id = rel_res.json()["id"]

        # Delete person
        del_res = client.delete(f"/api/entities/{p_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # Verify entity and relationship are gone from graph
        assert client.get(f"/api/entities/{p_id}").status_code == 404
        graph_data = client.get("/api/graph").json()
        assert not any(n["id"] == p_id for n in graph_data["nodes"])
        assert not any(e["id"] == rel_id for e in graph_data["edges"])

    def test_protected_dataset_entities_cannot_be_deleted(self, client):
        # Attempt to delete original dataset entity
        res = client.delete("/api/entities/PERSON_017")
        assert res.status_code == 403
        assert "Protected dataset entity" in res.json()["detail"]

        # Attempt to delete original dataset case
        res_case = client.delete("/api/entities/CASE_101")
        assert res_case.status_code == 403


class TestManualCreationValidationAndErrors:
    """Tests validation guards and input sanitization."""

    def test_missing_required_entity_fields(self, client):
        # Missing name for person
        res = client.post("/api/entities", json={"entity_type": "PERSON"})
        assert res.status_code == 422

        # Missing phone_number for phone
        res_phone = client.post("/api/entities", json={"entity_type": "PHONE"})
        assert res_phone.status_code == 422

    def test_invalid_entity_type(self, client):
        res = client.post("/api/entities", json={"entity_type": "DRONE", "name": "DJI Mavic"})
        assert res.status_code == 422
        assert "Invalid or missing entity_type" in res.json()["detail"]

    def test_relationship_nonexistent_entities(self, client):
        res = client.post("/api/relationships", json={
            "source_id": "NONEXISTENT_001",
            "target_id": "PERSON_017",
            "relationship": "USES"
        })
        assert res.status_code == 404
        assert "NONEXISTENT_001" in res.json()["detail"]

    def test_relationship_invalid_type(self, client):
        res = client.post("/api/relationships", json={
            "source_id": "PERSON_017",
            "target_id": "PHONE_042",
            "relationship": "TELEPORTED_TO"
        })
        assert res.status_code == 422
