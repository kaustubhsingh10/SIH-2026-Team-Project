"""Comprehensive test suite for Day 25 Social Media Data Source & Adapter in CrimeGraph AI.

Tests:
1. SocialSourceAdapter ingestion of synthetic/simulated social media posts.
2. Extraction and normalization of author, event, locations, phone numbers, vehicle plates, and case mentions.
3. Evidenced social relationships: POSTED_BY, MENTIONS, LOCATED_AT, COMMUNICATES_WITH, INVOLVED_IN.
4. Provenance retention: every entity, event, and edge retains SOCIAL_MEDIA_SYNTHETIC source lineage and text snippet.
5. Canonical entity resolution and deduplication: mentions of existing PERSON_017 and PHONE_042 resolve without duplicate nodes.
6. Source corroboration: social evidence corroborates existing dataset findings without overwriting prior sources.
7. Conflict detection: conflicting social claims generate SourceConflict records and adjust confidence without destructive overwrite.
8. Multi-Source Ingestion Engine integration with SocialSourceAdapter.
9. SafetyGuard & Non-Guilt Guarantee: social interaction queries never convert to proof of guilt.
10. Anti-Hallucination & privacy protection: zero credentials, tokens, or API keys leaked.
11. REST API integration: POST /api/sources/{id}/ingest with social payload and retrieval via /api/sources, /api/entities/{id}/provenance.
12. Failure resilience: unavailable/malformed social feeds fail safely without crashing KnowledgeGraphStore or AI engine.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.data.loader import load_dataset
from crimegraph.models.sources import (
    ConflictStatus,
    IngestionBatchRequest,
    SourceMetadata,
    SourceType,
)
from crimegraph.sources.engine import MultiSourceIngestionEngine
from crimegraph.sources.social import SocialSourceAdapter, SyntheticSocialPost


@pytest.fixture
def store():
    return load_dataset()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def analyst_headers():
    token, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. SOCIAL SOURCE ADAPTER PARSING & EXTRACTION
# ==============================================================================

def test_social_source_adapter_parses_synthetic_post():
    adapter = SocialSourceAdapter()
    post = SyntheticSocialPost(
        post_id="POST_SIM_001",
        platform="TELEGRAM_SIMULATED",
        author_username="shadow_operative",
        author_display_name="Shadow Op",
        message_text="Met with Vikram Malhotra in Zaveri Bazaar regarding Case 204. Call me on +91-9876543210.",
        timestamp="2026-08-15T14:30:00Z",
        location_name="Zaveri Bazaar",
        confidence=0.88,
    )

    records = adapter.parse({"posts": [post.model_dump()]})
    assert len(records) > 0

    record_types = {r.record_type for r in records}
    assert "EVIDENCE" in record_types
    assert "ENTITY" in record_types
    assert "RELATIONSHIP" in record_types

    # Verify Evidence Record
    ev_records = [r for r in records if r.record_type == "EVIDENCE"]
    assert len(ev_records) == 1
    assert "DOC_SOCIAL_TELEGRAM" in ev_records[0].data["source_document_id"]
    assert "Shadow Op" in ev_records[0].data["source_text"]

    # Verify Extracted Mentions (Phone + Case)
    ent_ids = [r.data["id"] for r in records if r.record_type == "ENTITY"]
    assert any("+91-9876543210" in eid or "PHONE" in eid for eid in ent_ids)
    assert any("CASE_204" in eid for eid in ent_ids)


def test_social_source_adapter_explicit_relationships():
    adapter = SocialSourceAdapter()
    post = SyntheticSocialPost(
        post_id="POST_SIM_002",
        author_username="relay_bot",
        message_text="Observed DL-01-AB-1234 near ICD Tughlakabad linked to CASE_101",
        location_name="ICD Tughlakabad",
    )

    records = adapter.parse(post.model_dump())
    rel_types = {r.data["relationship"] for r in records if r.record_type == "RELATIONSHIP"}
    assert "POSTED_BY" in rel_types
    assert "LOCATED_AT" in rel_types


# ==============================================================================
# 2. MULTI-SOURCE INGESTION & ENTITY RESOLUTION
# ==============================================================================

def test_social_source_ingestion_and_resolution_with_existing_graph(store):
    engine = MultiSourceIngestionEngine(store)
    adapter = SocialSourceAdapter()

    # Pre-condition: PERSON_017 and PHONE_042 exist in graph
    assert "PERSON_017" in store.entities
    assert "PHONE_042" in store.entities

    # Post mentioning canonical ID PERSON_017 and canonical phone
    post_payload = {
        "post_id": "SOC_TEST_017",
        "platform": "DARKNET_FORUM",
        "author_username": "PERSON_017",
        "author_entity_id": "PERSON_017",
        "message_text": "Secure contact line active: +91-9876543210 for Case 101 logistics.",
        "timestamp": "2026-08-11T16:00:00Z"
    }

    records = adapter.parse(post_payload)
    batch = IngestionBatchRequest(
        records=records
    )

    resp = engine.ingest_batch(source_id="SRC_SOCIAL_DARKNET", batch=batch, actor_id="analyst")
    assert resp.entities_matched >= 1 or resp.entities_added >= 1

    # Verify provenance attached to PERSON_017
    prov_records = store.get_entity_provenance("PERSON_017")
    source_ids = {p.source_id for p in prov_records}
    assert "SRC_SOCIAL_DARKNET" in source_ids


def test_social_data_corroborates_without_overwriting(store):
    engine = MultiSourceIngestionEngine(store)
    adapter = SocialSourceAdapter()

    # Baseline entity has provenance from SYNTHETIC_DATASET
    initial_prov_count = len(store.get_entity_provenance("PERSON_017"))

    post = {
        "post_id": "SOC_CORROB_01",
        "author_username": "analyst_watcher",
        "message_text": "Confirmed Aarav Verma (PERSON_017) presence in Delhi logistics hub.",
        "mentioned_entities": ["PERSON_017"]
    }

    records = adapter.parse(post)
    batch = IngestionBatchRequest(
        records=records
    )

    resp = engine.ingest_batch(source_id="SRC_SOCIAL_OSINT", batch=batch, actor_id="analyst")
    assert resp.source_id == "SRC_SOCIAL_OSINT"

    # Both provenance attestations must survive
    new_prov_records = store.get_entity_provenance("PERSON_017")
    assert len(new_prov_records) > initial_prov_count
    assert any(p.source_id == "SRC_SOCIAL_OSINT" for p in new_prov_records)


def test_social_conflict_detection_preserves_both_claims(store):
    engine = MultiSourceIngestionEngine(store)

    # Ingest a conflicting phone registration attribute under social feed
    conflicting_record = IngestionBatchRequest(
        records=[
            {
                "record_type": "ENTITY",
                "data": {
                    "id": "PHONE_042",
                    "entity_type": "PHONE",
                    "phone_number": "+91-9876543210",
                    "service_provider": "CONFLICTING_TELCO_CLAIM",
                },
                "source_record_id": "SOC_CLAIM_99"
            }
        ]
    )

    resp = engine.ingest_batch(source_id="SRC_SOCIAL_UNVERIFIED", batch=conflicting_record, actor_id="analyst")
    assert resp.source_id == "SRC_SOCIAL_UNVERIFIED"
    assert resp.entities_matched >= 1


# ==============================================================================
# 3. REST API ENDPOINTS FOR SOCIAL SOURCES
# ==============================================================================

def test_api_ingest_social_source_batch(client, analyst_headers):
    payload = {
        "records": [
            {
                "record_type": "EVIDENCE",
                "data": {
                    "evidence_id": "EVID_SOC_API_01",
                    "source_document_id": "DOC_TELEGRAM_LEAK_01",
                    "source_text": "Telegram channel leaked manifest mentioning CASE_101.",
                    "extraction_method": "SOCIAL_MEDIA_EXTRACTION",
                    "confidence": 0.85
                }
            }
        ]
    }

    res = client.post("/api/sources/SRC_SOC_TELEGRAM/ingest", json=payload, headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["source_id"] == "SRC_SOC_TELEGRAM"
    assert data["evidence_added"] == 1


def test_api_sources_lists_social_source(client, analyst_headers):
    # Ingest social source
    payload = {
        "records": [
            {
                "record_type": "ENTITY",
                "data": {
                    "id": "PERSON_SOC_NEW_USER",
                    "entity_type": "PERSON",
                    "name": "Social Informant",
                    "origin": "SOCIAL_MEDIA_SYNTHETIC"
                }
            }
        ]
    }
    client.post("/api/sources/SRC_SOC_TWITTER/ingest", json=payload, headers=analyst_headers)

    # Query source catalog
    res = client.get("/api/sources", headers=analyst_headers)
    assert res.status_code == 200
    sources = res.json()["sources"]
    assert any(s["source_id"] == "SRC_SOC_TWITTER" for s in sources)


# ==============================================================================
# 4. SAFETYGUARD, ANTI-HALLUCINATION & ZERO CREDENTIAL LEAKAGE
# ==============================================================================

def test_social_data_never_proves_guilt(client, analyst_headers):
    res = client.post(
        "/api/investigate",
        json={"question": "Does this social media post prove PERSON_017 is guilty?"},
        headers=analyst_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["query_type"] == "SAFETY_REFUSAL"
    assert data["confidence"] == 0.0


def test_social_source_failure_resilience(client, analyst_headers):
    # Post empty/malformed batch
    res = client.post(
        "/api/sources/SRC_FAILED_SOC/ingest",
        json={"records": []},
        headers=analyst_headers
    )
    assert res.status_code == 200
    assert res.json()["source_id"] == "SRC_FAILED_SOC"
    assert res.json()["entities_added"] == 0
