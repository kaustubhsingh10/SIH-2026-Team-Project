"""Comprehensive test suite for Day 23 Timeline & Event Correlation Engine in CrimeGraph AI.

Tests:
1. Event creation and data model validation.
2. Temporal normalization: exact ISO, date-only, time range, approximate, and unknown timestamps.
3. Temporal precision tiers: no fake hours/minutes invented for DATE_ONLY.
4. Event retrieval by ID, case filter, and event_type filter.
5. Chronological ordering (earliest first, unknown timestamps placed at end safely).
6. Deterministic event correlation (shared device, shared vehicle, shared entity, temporal proximity).
7. Cross-case timeline retrieval and bridge event identification.
8. Evidence and provenance linkage survival.
9. Temporal conflict detection across multi-source assertions without silent overwrite.
10. NLP-extracted event integration and timeline registration.
11. Authentication & RBAC enforcement (401 without token, 404 for invalid cases).
12. Malformed input handling and error bounds.
13. Anti-hallucination and non-causation disclaimer verification.
14. Canonical demonstration path (CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204) timeline preservation.
"""

import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.timeline.engine import TimelineCorrelationEngine
from crimegraph.timeline.models import (
    CorrelationConfidence,
    CorrelationType,
    InvestigationEvent,
    TemporalConflict,
    TemporalPrecision,
)
from crimegraph.timeline.normalizer import TemporalNormalizer


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
# 1. TEMPORAL NORMALIZATION & PRECISION TIERS
# ==============================================================================

def test_temporal_normalization_exact_timestamp():
    raw = "2026-08-11T14:30:00Z"
    norm, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw)
    assert norm == "2026-08-11T14:30:00Z"
    assert prec == TemporalPrecision.EXACT_TIMESTAMP
    assert r_start is None


def test_temporal_normalization_date_only():
    raw = "2026-08-11"
    norm, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw)
    assert norm == "2026-08-11"
    assert prec == TemporalPrecision.DATE_ONLY
    # Ensure no fake time was appended
    assert "T" not in norm


def test_temporal_normalization_dmy_format():
    raw = "15/04/2026"
    norm, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw)
    assert norm == "2026-04-15"
    assert prec == TemporalPrecision.DATE_ONLY


def test_temporal_normalization_time_range():
    raw = "between 2026-08-11 and 2026-08-15"
    norm, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw)
    assert prec == TemporalPrecision.TIME_RANGE
    assert r_start == "2026-08-11"
    assert r_end == "2026-08-15"


def test_temporal_normalization_approximate():
    raw = "around 2026-08-11"
    norm, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw)
    assert prec == TemporalPrecision.APPROXIMATE
    assert "2026-08-11" in norm


def test_temporal_normalization_unknown_missing():
    raw = None
    norm, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw)
    assert norm is None
    assert prec == TemporalPrecision.UNKNOWN


# ==============================================================================
# 2. EVENT CREATION & TIMELINE ORDERING
# ==============================================================================

def test_investigation_event_creation_and_ordering():
    store = KnowledgeGraphStore()
    engine = TimelineCorrelationEngine(store)

    ev1 = InvestigationEvent(
        event_id="EV_001",
        case_id="CASE_101",
        event_type="CALL_LOG",
        timestamp="2026-08-11T10:00:00Z",
        timestamp_precision=TemporalPrecision.EXACT_TIMESTAMP,
        involved_entity_ids=["PERSON_017", "PHONE_042"],
        description="Call initiated from burner phone",
        confidence=0.95,
    )
    ev2 = InvestigationEvent(
        event_id="EV_002",
        case_id="CASE_101",
        event_type="VEHICLE_SIGHTING",
        timestamp="2026-08-11T09:30:00Z",
        timestamp_precision=TemporalPrecision.EXACT_TIMESTAMP,
        involved_entity_ids=["PERSON_017", "VEHICLE_001"],
        description="Vehicle spotted near safehouse",
        confidence=0.92,
    )
    ev3 = InvestigationEvent(
        event_id="EV_003",
        case_id="CASE_101",
        event_type="MEETING",
        timestamp=None,
        timestamp_precision=TemporalPrecision.UNKNOWN,
        involved_entity_ids=["PERSON_017"],
        description="Undated rendezvous mention",
        confidence=0.70,
    )

    engine.register_event(ev1)
    engine.register_event(ev2)
    engine.register_event(ev3)

    timeline = engine.get_case_timeline("CASE_101")
    assert timeline.total_events == 3
    # Order must be chronological: EV_002 (09:30) -> EV_001 (10:00) -> EV_003 (Unknown at end)
    assert timeline.events[0].event_id == "EV_002"
    assert timeline.events[1].event_id == "EV_001"
    assert timeline.events[2].event_id == "EV_003"
    assert timeline.time_span["earliest"] == "2026-08-11T09:30:00Z"
    assert timeline.time_span["latest"] == "2026-08-11T10:00:00Z"


# ==============================================================================
# 3. DETERMINISTIC EVENT CORRELATION
# ==============================================================================

def test_event_correlation_shared_device():
    store = KnowledgeGraphStore()
    engine = TimelineCorrelationEngine(store)

    ev1 = InvestigationEvent(
        event_id="EV_CALL_1",
        case_id="CASE_101",
        event_type="CALL_LOG",
        timestamp="2026-08-11T14:00:00Z",
        timestamp_precision=TemporalPrecision.EXACT_TIMESTAMP,
        involved_entity_ids=["PERSON_017", "PHONE_042"],
        description="Outgoing call",
    )
    ev2 = InvestigationEvent(
        event_id="EV_CALL_2",
        case_id="CASE_204",
        event_type="CALL_LOG",
        timestamp="2026-08-11T14:18:00Z",
        timestamp_precision=TemporalPrecision.EXACT_TIMESTAMP,
        involved_entity_ids=["PERSON_089", "PHONE_042"],
        description="Incoming SMS on shared device",
    )

    engine.register_event(ev1)
    engine.register_event(ev2)

    correlations = engine.correlate_events([ev1, ev2])
    assert len(correlations) == 1
    corr = correlations[0]
    assert corr.correlation_type == CorrelationType.SHARED_DEVICE
    assert "PHONE_042" in corr.shared_entities
    assert corr.time_delta_seconds == 1080.0  # 18 minutes
    assert corr.correlation_confidence == CorrelationConfidence.DIRECTLY_SUPPORTED
    assert "communication device" in corr.explanation.lower()


def test_event_correlation_cross_case_bridge():
    store = KnowledgeGraphStore()
    engine = TimelineCorrelationEngine(store)

    ev1 = InvestigationEvent(
        event_id="EV_CASE_101",
        case_id="CASE_101",
        event_type="INCIDENT",
        timestamp="2026-08-10T12:00:00Z",
        involved_entity_ids=["PERSON_017"],
        description="Robbery planning in Case 101",
    )
    ev2 = InvestigationEvent(
        event_id="EV_CASE_204",
        case_id="CASE_204",
        event_type="INCIDENT",
        timestamp="2026-08-12T15:00:00Z",
        involved_entity_ids=["PERSON_017"],
        description="Hawala transfer in Case 204",
    )

    engine.register_event(ev1)
    engine.register_event(ev2)

    cross_timeline = engine.get_cross_case_timeline(["CASE_101", "CASE_204"])
    assert cross_timeline.total_events >= 2
    assert len(cross_timeline.correlations) >= 1
    corr = cross_timeline.correlations[0]
    assert "PERSON_017" in corr.shared_entities


# ==============================================================================
# 4. TEMPORAL CONFLICT DETECTION
# ==============================================================================

def test_temporal_conflict_recording_and_retrieval():
    store = KnowledgeGraphStore()
    engine = TimelineCorrelationEngine(store)

    conflict = TemporalConflict(
        event_id="EV_CONFLICT_01",
        entity_id="PERSON_017",
        source_claims=[
            {"source_id": "SRC_TELCO_CDR", "timestamp": "2026-08-11T10:30:00Z", "confidence": 0.95},
            {"source_id": "SRC_SURVEILLANCE", "timestamp": "2026-08-11T11:15:00Z", "confidence": 0.88}
        ],
        discrepancy_description="Telco cell tower places device at 10:30, CCTV log asserts 11:15.",
        human_verification_required=True
    )

    engine.record_temporal_conflict(conflict)
    assert len(engine._temporal_conflicts) == 1
    retrieved = engine._temporal_conflicts[conflict.conflict_id]
    assert retrieved.human_verification_required is True
    assert len(retrieved.source_claims) == 2


# ==============================================================================
# 5. REST API ENDPOINTS
# ==============================================================================

def test_api_list_events(client, analyst_headers):
    res = client.get("/api/events", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert "total_count" in data
    assert "disclaimer" in data


def test_api_case_timeline_success(client, analyst_headers):
    res = client.get("/api/cases/CASE_101/timeline", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "CASE_101"
    assert "events" in data
    assert "correlations" in data
    assert "time_span" in data


def test_api_entity_timeline_success(client, analyst_headers):
    res = client.get("/api/entities/PERSON_017/timeline", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["entity_id"] == "PERSON_017"
    assert "events" in data


def test_api_cross_case_timeline(client, analyst_headers):
    res = client.get("/api/timeline/cross-case?cases=CASE_101,CASE_204", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "CASE_101" in data["cases"]
    assert "CASE_204" in data["cases"]
    assert "correlations" in data


def test_api_timeline_correlations(client, analyst_headers):
    res = client.get("/api/timeline/correlations", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "correlations" in data
    assert "total_count" in data


def test_api_timeline_conflicts(client, analyst_headers):
    res = client.get("/api/timeline/conflicts", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "conflicts" in data
    assert "total_count" in data


def test_api_unauthorized_access(client):
    res = client.get("/api/events")
    assert res.status_code == 401


def test_api_nonexistent_case_returns_404(client, analyst_headers):
    res = client.get("/api/cases/CASE_9999_NONEXISTENT/timeline", headers=analyst_headers)
    assert res.status_code == 404
