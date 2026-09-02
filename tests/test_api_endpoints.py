"""Automated test suite for CrimeGraph AI REST API endpoints.

Tests all endpoints against API_CONTRACT.md and DATA_SCHEMA.md.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.generator import generate_synthetic_investigation_data


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient initialized with the deterministic synthetic dataset."""
    graph = generate_synthetic_investigation_data()
    app = create_app(graph_instance=graph)
    with TestClient(app) as test_client:
        yield test_client


class TestSystemEndpoints:
    def test_root_status(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["metrics"]["entity_count"] > 0
        assert data["metrics"]["relationship_count"] > 0

    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCasesAPI:
    def test_list_cases(self, client):
        response = client.get("/api/cases")
        assert response.status_code == 200
        cases = response.json()
        assert len(cases) >= 4
        case_ids = [c["id"] for c in cases]
        assert "CASE_101" in case_ids
        assert "CASE_204" in case_ids

    def test_list_cases_filter_status(self, client):
        response = client.get("/api/cases?status=ACTIVE")
        assert response.status_code == 200
        cases = response.json()
        assert all(c["status"] == "ACTIVE" for c in cases)

    def test_get_case_details_success(self, client):
        response = client.get("/api/cases/CASE_101")
        assert response.status_code == 200
        case = response.json()
        assert case["id"] == "CASE_101"
        assert case["case_number"] == "FIR-2026-DEL-101"
        assert "Operation Midnight Shadow" in case["title"]

    def test_get_case_details_not_found(self, client):
        response = client.get("/api/cases/CASE_NON_EXISTENT")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_case_graph(self, client):
        response = client.get("/api/cases/CASE_101/graph")
        assert response.status_code == 200
        subgraph = response.json()
        assert "nodes" in subgraph
        assert "edges" in subgraph
        node_ids = [n["id"] for n in subgraph["nodes"]]
        assert "CASE_101" in node_ids
        assert "PERSON_017" in node_ids
        assert "PHONE_042" in node_ids

    def test_get_case_entities(self, client):
        response = client.get("/api/cases/CASE_101/entities")
        assert response.status_code == 200
        entities = response.json()
        assert len(entities) > 0
        
        # Test type filter
        response_persons = client.get("/api/cases/CASE_101/entities?entity_type=PERSON")
        assert response_persons.status_code == 200
        persons = response_persons.json()
        assert all(p["entity_type"] == "PERSON" for p in persons)

    def test_get_case_timeline(self, client):
        response = client.get("/api/cases/CASE_101/timeline")
        assert response.status_code == 200
        timeline = response.json()
        assert "events" in timeline
        events = timeline["events"]
        assert len(events) >= 1
        for ev in events:
            assert "id" in ev
            assert "type" in ev
            assert "timestamp" in ev

    def test_create_case_success(self, client):
        payload = {
            "title": "Operation Northern Lights — Trans-State Syndicate",
            "case_type": "Logistics Hijack",
            "priority": "HIGH",
            "status": "ACTIVE",
            "location": "LOC_001",
            "description": "Intercepted cargo syndicate operating across northern state borders.",
            "notes": "Initial lead from telco intercept.",
            "created_by": "OFFICER_VERMA"
        }
        response = client.post("/api/cases", json=payload)
        assert response.status_code == 201
        created = response.json()
        assert created["title"] == "Operation Northern Lights — Trans-State Syndicate"
        assert created["entity_type"] == "CASE"
        assert created["id"].startswith("CASE_")
        assert created["status"] == "ACTIVE"

        # Verify case is now listed
        list_res = client.get("/api/cases")
        assert list_res.status_code == 200
        case_ids = [c["id"] for c in list_res.json()]
        assert created["id"] in case_ids

        # Verify case detail retrieval
        detail_res = client.get(f"/api/cases/{created['id']}")
        assert detail_res.status_code == 200
        assert detail_res.json()["title"] == "Operation Northern Lights — Trans-State Syndicate"

    def test_create_case_validation_missing_title(self, client):
        payload = {
            "description": "Case without title"
        }
        response = client.post("/api/cases", json=payload)
        assert response.status_code == 422
        assert "title" in response.json()["detail"].lower()

    def test_create_case_duplicate_id(self, client):
        payload = {
            "id": "CASE_101",
            "title": "Duplicate Case 101 Attempt"
        }
        response = client.post("/api/cases", json=payload)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_case_attach_entity_and_relationship(self, client):
        # 1. Create a new case
        case_res = client.post("/api/cases", json={"title": "Operation Alpha Falcon — Money Laundering"})
        assert case_res.status_code == 201
        new_case_id = case_res.json()["id"]

        # 2. Create a new entity
        ent_res = client.post("/api/entities", json={"type": "PERSON", "name": "Rohan Sharma", "age": 34})
        assert ent_res.status_code == 201
        person_id = ent_res.json()["id"]

        # 3. Connect person to new case
        rel_res = client.post("/api/relationships", json={
            "source_id": person_id,
            "relationship": "INVOLVED_IN",
            "target_id": new_case_id,
            "confidence": 0.95
        })
        assert rel_res.status_code == 201

        # 4. Verify case graph contains both nodes and the edge
        graph_res = client.get(f"/api/cases/{new_case_id}/graph")
        assert graph_res.status_code == 200
        nodes = [n["id"] for n in graph_res.json()["nodes"]]
        assert new_case_id in nodes
        assert person_id in nodes



class TestMainDemoCrossCaseAPI:
    def test_main_demo_path_discovery(self, client):
        """CRITICAL: Tests discovery of the exact demo connection chain:
        CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204
        """
        response = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        connections = data["connections"]
        assert len(connections) >= 1

        expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        matching = [c for c in connections if c["path"] == expected_path]
        assert len(matching) == 1, f"Expected demo path {expected_path} not found in {connections}"

        demo_conn = matching[0]
        assert demo_conn["case_a"] == "CASE_101"
        assert demo_conn["case_b"] == "CASE_204"
        assert "PHONE_042" in demo_conn["shared_entities"]
        assert demo_conn["confidence"] >= 0.90
        assert "EVID_042_01" in demo_conn["evidence_ids"]
        assert "EVID_042_02" in demo_conn["evidence_ids"]

    def test_cross_case_connections_invalid_case(self, client):
        response = client.get("/api/cases/connections?case_a=CASE_101&case_b=INVALID_CASE")
        assert response.status_code == 404


class TestEntitiesAPI:
    def test_list_entities_all(self, client):
        response = client.get("/api/entities")
        assert response.status_code == 200
        entities = response.json()
        assert len(entities) >= 25

    def test_list_entities_filter_type(self, client):
        response = client.get("/api/entities?type=PERSON")
        assert response.status_code == 200
        persons = response.json()
        assert len(persons) >= 5
        assert all(p["entity_type"] == "PERSON" for p in persons)

    def test_list_entities_search(self, client):
        response = client.get("/api/entities?search=Aarav")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["id"] == "PERSON_017"

    def test_list_entities_min_confidence(self, client):
        response = client.get("/api/entities?min_confidence=0.95")
        assert response.status_code == 200
        results = response.json()
        assert all(r.get("confidence", 1.0) >= 0.95 for r in results)

    def test_get_entity_details_success(self, client):
        response = client.get("/api/entities/PERSON_017")
        assert response.status_code == 200
        entity = response.json()
        assert entity["id"] == "PERSON_017"
        assert entity["type"] == "PERSON"
        assert entity["name"] == "Aarav Verma"
        assert len(entity["relationships"]) >= 4
        assert "CASE_101" in entity["cases"]
        assert len(entity["evidence"]) >= 1

    def test_get_entity_details_not_found(self, client):
        response = client.get("/api/entities/PERSON_9999")
        assert response.status_code == 404

    def test_get_entity_neighbors(self, client):
        response = client.get("/api/entities/PHONE_042/neighbors")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "PHONE_042"
        assert data["neighbor_count"] >= 2
        neighbor_ids = [n["neighbor"]["id"] for n in data["neighbors"]]
        assert "PERSON_017" in neighbor_ids
        assert "PERSON_089" in neighbor_ids


class TestGraphAPI:
    def test_get_full_graph(self, client):
        response = client.get("/api/graph")
        assert response.status_code == 200
        graph_data = response.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) >= 25
        assert len(graph_data["edges"]) >= 20

    def test_get_graph_filter_relationship(self, client):
        response = client.get("/api/graph?relationship_type=USES")
        assert response.status_code == 200
        graph_data = response.json()
        assert all(e["relationship"] == "USES" for e in graph_data["edges"])

    def test_get_paths_between_entities(self, client):
        response = client.get("/api/paths?source_id=PERSON_017&target_id=PERSON_089")
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "PERSON_017"
        assert data["target_id"] == "PERSON_089"
        assert data["path_count"] >= 1
        # Main connecting path through phone: PERSON_017 -> PHONE_042 -> PERSON_089
        paths = [p["path"] for p in data["paths"]]
        assert ["PERSON_017", "PHONE_042", "PERSON_089"] in paths

    def test_get_paths_invalid_target(self, client):
        response = client.get("/api/paths?source_id=PERSON_017&target_id=NON_EXISTENT")
        assert response.status_code == 404


class TestEvidenceAPI:
    def test_list_evidence_all(self, client):
        response = client.get("/api/evidence")
        assert response.status_code == 200
        evidence_list = response.json()
        assert len(evidence_list) >= 15

    def test_list_evidence_filter_document(self, client):
        response = client.get("/api/evidence?source_document_id=FIR_REPORT")
        assert response.status_code == 200
        results = response.json()
        assert len(results) >= 1
        assert all("FIR_REPORT" in ev["source_document_id"] for ev in results)

    def test_get_evidence_item_success(self, client):
        response = client.get("/api/evidence/EVID_042_01")
        assert response.status_code == 200
        ev = response.json()
        assert ev["evidence_id"] == "EVID_042_01"
        assert ev["confidence_tier"] == "High"
        assert "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf" in ev["source_document_id"]
        assert "+91-9876543210" in ev["source_text"]

    def test_get_evidence_item_not_found(self, client):
        response = client.get("/api/evidence/EVID_DOES_NOT_EXIST")
        assert response.status_code == 404


class TestManualEntityAndRelationshipAPI:
    def test_create_manual_person_entity(self, client):
        payload = {
            "type": "PERSON",
            "name": "Test Manual Person",
            "age": 30,
            "gender": "Male",
            "details": "Created during automated testing"
        }
        response = client.post("/api/entities", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Manual Person"
        assert data["entity_type"] == "PERSON"
        assert data["id"].startswith("PERSON_")

        # Test updating the manual entity
        update_payload = {"name": "Updated Manual Person", "age": 31}
        update_res = client.put(f"/api/entities/{data['id']}", json=update_payload)
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Updated Manual Person"
        assert update_res.json()["age"] == 31

        # Test creating a relationship connecting this entity to PERSON_017
        rel_payload = {
            "source_id": data["id"],
            "relationship": "CONTACTED",
            "target_id": "PERSON_017",
            "confidence": 0.92
        }
        rel_res = client.post("/api/relationships", json=rel_payload)
        assert rel_res.status_code == 201
        rel_data = rel_res.json()
        assert rel_data["source_id"] == data["id"]
        assert rel_data["target_id"] == "PERSON_017"
        assert rel_data["relationship"] == "CONTACTED"

        # Test deleting the manual entity
        del_res = client.delete(f"/api/entities/{data['id']}")
        assert del_res.status_code == 200
        assert del_res.json()["deleted_id"] == data["id"]

        # Verify entity no longer exists
        get_res = client.get(f"/api/entities/{data['id']}")
        assert get_res.status_code == 404


