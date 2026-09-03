"""Comprehensive test suite for Day 21 Multi-Source Data Layer in CrimeGraph AI.

Tests all 10 core requirements:
1. Multiple sources can coexist.
2. Same entity can have multiple provenance records.
3. Same relationship can have multiple supporting sources.
4. Source filtering works.
5. Provenance is preserved through graph traversal.
6. Conflicting source information is not silently merged.
7. Baseline dataset remains immutable.
8. Unauthorized source access is rejected.
9. AI receives source-aware grounded information.
10. Existing canonical path still works.
"""

import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.data.loader import get_default_dataset_path
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.sources import (
    ConflictStatus,
    IngestionBatchRequest,
    IngestionRecord,
    ProvenanceRecord,
    SourceConflict,
    SourceCreateRequest,
    SourceMetadata,
    SourceType,
)
from crimegraph.sources.engine import MultiSourceIngestionEngine
from crimegraph.sources.normalizer import DataNormalizer
from crimegraph.sources.resolver import SourceAwareEntityResolver


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def analyst_auth_headers():
    token, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. MULTIPLE SOURCES CAN COEXIST
# ==============================================================================

def test_multiple_sources_coexist_in_store():
    store = KnowledgeGraphStore()
    assert len(store.list_sources()) >= 2  # Baseline + Manual
    
    src1 = SourceMetadata(
        source_id="SRC_CASE_101",
        source_type=SourceType.CASE_RECORD,
        source_name="Case 101 FIR Dossier",
        confidence=0.95
    )
    src2 = SourceMetadata(
        source_id="SRC_INTEL_GANG",
        source_type=SourceType.INTELLIGENCE_SOURCE,
        source_name="Field Intelligence Brief 42",
        confidence=0.88
    )
    store.register_source(src1)
    store.register_source(src2)

    assert store.get_source("SRC_CASE_101") is not None
    assert store.get_source("SRC_INTEL_GANG") is not None
    assert len(store.list_sources()) >= 4


def test_api_list_and_register_sources(client, analyst_auth_headers):
    # List sources
    res = client.get("/api/sources", headers=analyst_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    assert data["total_count"] >= 2

    # Register new source
    new_src = {
        "source_id": "SRC_TEST_INGEST_01",
        "source_type": "CASE_RECORD",
        "source_name": "Test Case Registry Feed",
        "confidence": 0.92,
        "description": "Feed from regional crime database"
    }
    res_reg = client.post("/api/sources", json=new_src, headers=analyst_auth_headers)
    assert res_reg.status_code == 201
    assert res_reg.json()["source"]["source_id"] == "SRC_TEST_INGEST_01"

    # Verify retrieval
    res_get = client.get("/api/sources/SRC_TEST_INGEST_01", headers=analyst_auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["source_name"] == "Test Case Registry Feed"


# ==============================================================================
# 2. SAME ENTITY CAN HAVE MULTIPLE PROVENANCE RECORDS
# ==============================================================================

def test_entity_multiple_provenance_records(client, analyst_auth_headers):
    # Query provenance for existing entity PERSON_017
    res = client.get("/api/entities/PERSON_017/sources", headers=analyst_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["entity_id"] == "PERSON_017"
    assert len(data["provenance"]) >= 1

    # Ingest additional observation of PERSON_017 from a separate source
    ingest_payload = {
        "records": [
            {
                "record_type": "ENTITY",
                "data": {
                    "entity_type": "PERSON",
                    "name": "Aarav Verma",
                    "phone_ids": ["PHONE_042"]
                },
                "source_record_id": "INTEL_REC_9981",
                "source_text": "Informant confirmed Aarav Verma operates burner line in Rohini."
            }
        ],
        "auto_resolve": True,
        "record_conflicts": True
    }
    res_ingest = client.post("/api/sources/SRC_INTEL_FEED_01/ingest", json=ingest_payload, headers=analyst_auth_headers)
    assert res_ingest.status_code == 200
    ing_res = res_ingest.json()
    assert ing_res["entities_matched"] == 1

    # Verify entity now has at least 2 distinct provenance records
    res2 = client.get("/api/entities/PERSON_017/sources", headers=analyst_auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    sources = set(p["source_id"] for p in data2["provenance"])
    assert "SRC_SYNTHETIC_DATASET" in sources or "SRC_MANUAL_ENTRY" in sources
    assert "SRC_INTEL_FEED_01" in sources
    assert data2["total_sources"] >= 2


# ==============================================================================
# 3. SAME RELATIONSHIP CAN HAVE MULTIPLE SUPPORTING SOURCES
# ==============================================================================

def test_relationship_multiple_supporting_sources(client, analyst_auth_headers):
    # Ingest supporting observation for existing relationship PERSON_017 -> USES -> PHONE_042
    ingest_payload = {
        "records": [
            {
                "record_type": "RELATIONSHIP",
                "data": {
                    "source_id": "PERSON_017",
                    "target_id": "PHONE_042",
                    "relationship": "USES",
                    "confidence": 0.96,
                    "evidence_ids": ["EVID_INTEL_SUPP_01"]
                },
                "source_record_id": "TELCO_CDR_LINE_042",
                "source_text": "Tower dump corroborates active CDR link."
            }
        ],
        "auto_resolve": True,
        "record_conflicts": True
    }
    res = client.post("/api/sources/SRC_TELCO_CDR/ingest", json=ingest_payload, headers=analyst_auth_headers)
    assert res.status_code == 200

    # Retrieve all relationships to find the USES relationship ID
    res_rels = client.get("/api/relationships", headers=analyst_auth_headers)
    assert res_rels.status_code == 200
    rel_id = None
    for r in res_rels.json():
        if r["source_id"] == "PERSON_017" and r["target_id"] == "PHONE_042" and r["relationship"] == "USES":
            rel_id = r["id"]
            break
    assert rel_id is not None

    # Query relationship source provenance
    res_prov = client.get(f"/api/relationships/{rel_id}/sources", headers=analyst_auth_headers)
    assert res_prov.status_code == 200
    prov_data = res_prov.json()
    assert prov_data["relationship_id"] == rel_id
    sources = set(p["source_id"] for p in prov_data["provenance"])
    assert "SRC_TELCO_CDR" in sources


# ==============================================================================
# 4. SOURCE FILTERING WORKS
# ==============================================================================

def test_source_filtering_entities_and_relationships(client, analyst_auth_headers):
    # Ingest unique entity under a custom source
    ingest_payload = {
        "records": [
            {
                "record_type": "ENTITY",
                "data": {
                    "id": "PERSON_CUSTOM_SRC_01",
                    "entity_type": "PERSON",
                    "name": "Karan Singhania",
                    "confidence": 0.88
                },
                "source_record_id": "CUSTOM_REC_01"
            }
        ],
        "auto_resolve": False
    }
    client.post("/api/sources/SRC_CUSTOM_REGIONAL/ingest", json=ingest_payload, headers=analyst_auth_headers)

    # Filter entities by source
    res = client.get("/api/sources/SRC_CUSTOM_REGIONAL/entities", headers=analyst_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["source_id"] == "SRC_CUSTOM_REGIONAL"
    assert any(e["id"] == "PERSON_CUSTOM_SRC_01" for e in data["entities"])


# ==============================================================================
# 5. PROVENANCE IS PRESERVED THROUGH GRAPH TRAVERSAL (PATH PROVENANCE)
# ==============================================================================

def test_path_provenance_preservation(client, analyst_auth_headers):
    path_nodes = "CASE_101,PERSON_017,PHONE_042,PERSON_089,CASE_204"
    res = client.get(f"/api/graph/path-provenance?nodes={path_nodes}", headers=analyst_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_steps"] == 4
    for step in data["steps"]:
        assert "source_node_provenance" in step
        assert len(step["source_node_provenance"]) >= 1
        assert "target_node_provenance" in step
        assert len(step["target_node_provenance"]) >= 1
        assert "relationship_provenance" in step


# ==============================================================================
# 6. CONFLICTING SOURCE INFORMATION IS NOT SILENTLY MERGED
# ==============================================================================

def test_conflicting_source_information_detected_and_recorded(client, analyst_auth_headers):
    # Ingest record for PERSON_017 asserting conflicting age (e.g. 45 vs baseline 28)
    ingest_payload = {
        "records": [
            {
                "record_type": "ENTITY",
                "data": {
                    "id": "PERSON_017",
                    "entity_type": "PERSON",
                    "name": "Aarav Verma",
                    "age": 45  # Discrepancy!
                },
                "source_record_id": "REG_DOC_771",
                "confidence": 0.85
            }
        ],
        "auto_resolve": True,
        "record_conflicts": True
    }
    res = client.post("/api/sources/SRC_SECONDARY_REGISTRY/ingest", json=ingest_payload, headers=analyst_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["conflicts_detected"] >= 1

    # Query conflicts endpoint
    res_conf = client.get("/api/sources/conflicts?target_id=PERSON_017", headers=analyst_auth_headers)
    assert res_conf.status_code == 200
    conf_data = res_conf.json()
    assert conf_data["total_count"] >= 1
    conflict = conf_data["conflicts"][0]
    assert conflict["target_id"] == "PERSON_017"
    assert conflict["field_name"] == "age"
    assert conflict["status"] == "DETECTED"

    # Resolve conflict with an analyst audit note
    conf_id = conflict["conflict_id"]
    resolve_payload = {
        "resolution_strategy": "MANUAL_OVERRIDE",
        "resolved_value": 28,
        "notes": "Verified against primary biometric registration; baseline 28 is authoritative."
    }
    res_res = client.post(f"/api/sources/conflicts/{conf_id}/resolve", json=resolve_payload, headers=analyst_auth_headers)
    assert res_res.status_code == 200
    assert res_res.json()["conflict"]["status"] == "RESOLVED"


# ==============================================================================
# 7. BASELINE DATASET REMAINS IMMUTABLE
# ==============================================================================

def test_baseline_dataset_immutability_and_hash():
    dataset_path = get_default_dataset_path()
    raw = dataset_path.read_bytes()
    curr_hash = hashlib.sha256(raw).hexdigest()
    assert curr_hash == "4b4ff1373eda9a8c4de685c5aa4949f3e1a02ce8aeb1c1eb10e398caf6aebcbb"


def test_baseline_entity_deletion_rejected(client, analyst_auth_headers):
    # Attempt to delete a baseline entity — must be rejected
    res = client.delete("/api/entities/PERSON_017", headers=analyst_auth_headers)
    assert res.status_code == 403


# ==============================================================================
# 8. UNAUTHORIZED SOURCE ACCESS IS REJECTED
# ==============================================================================

def test_unauthorized_source_access(client):
    # Unauthenticated list
    res_unauth = client.get("/api/sources")
    assert res_unauth.status_code == 401

    # Invalid token rejected
    bad_headers = {"Authorization": "Bearer invalid.jwt.token"}
    res_bad = client.get("/api/sources", headers=bad_headers)
    assert res_bad.status_code == 401


# ==============================================================================
# 9. AI RECEIVES SOURCE-AWARE GROUNDED INFORMATION
# ==============================================================================

def test_ai_investigation_source_aware_queries(client, analyst_auth_headers):
    # Query asking about sources for PERSON_017
    res = client.post(
        "/api/investigate",
        json={"question": "What data sources provide evidence for Person 017?"},
        headers=analyst_auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["query_type"] == "SOURCE_PROVENANCE"
    assert data["confidence"] >= 0.90
    assert "provenance" in data or "sources" in data
    assert data["is_safe"] is True

    # General sources summary query
    res_summary = client.post(
        "/api/investigate",
        json={"question": "List all active data feeds and sources"},
        headers=analyst_auth_headers
    )
    assert res_summary.status_code == 200
    data_sum = res_summary.json()
    assert data_sum["query_type"] in ("SOURCE_PROVENANCE", "SOURCE_SUMMARY")
    assert "sources" in data_sum or "provenance" in data_sum


# ==============================================================================
# 10. EXISTING CANONICAL PATH STILL WORKS
# ==============================================================================

def test_canonical_path_preservation(client, analyst_auth_headers):
    res = client.post(
        "/api/investigate",
        json={"question": "What is the connection between CASE_101 and CASE_204?"},
        headers=analyst_auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["query_type"] == "CROSS_CASE_CONNECTION"
    assert data["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
    assert data["confidence"] >= 0.90
    assert "EVID_042_01" in data["evidence_ids"]
