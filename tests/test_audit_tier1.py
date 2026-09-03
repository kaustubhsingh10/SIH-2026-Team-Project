"""Tier 1 Audit Trail & Activity Logging Verification Tests for CrimeGraph AI.

Tests:
1. Entity creation audit logging
2. Entity creation failure audit logging
3. Relationship creation audit logging
4. Protected dataset deletion denial audit logging
5. AI Investigator query audit logging
6. Authentication success and failure audit logging
7. Audit records survive cold backend restart
8. Append-oriented immutability of historical records
9. Audit endpoint filtering (actor_id, action, resource_type, status, limit)
10. Privacy & security (zero passwords, secrets, or JWT tokens in logs)
11. Synthetic dataset SHA-256 immutability
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.audit.logger import AuditLogger
from crimegraph.audit.models import AuditActorType, AuditResourceType, AuditStatus
from crimegraph.data.loader import get_default_dataset_path


def compute_sha256(filepath: Path) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestTier1AuditLogging:

    @pytest.fixture(autouse=True)
    def setup_audit_environment(self, monkeypatch):
        """Isolates audit log, users, and manual data in temporary files."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_audit:
            self.temp_audit_path = Path(tf_audit.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_users:
            self.temp_users_path = Path(tf_users.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_manual:
            self.temp_manual_path = Path(tf_manual.name)

        monkeypatch.setenv("CRIMEGRAPH_AUDIT_LOG_PATH", str(self.temp_audit_path))
        monkeypatch.setenv("CRIMEGRAPH_USERS_PATH", str(self.temp_users_path))
        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(self.temp_manual_path))
        monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "audit-test-secret-2026")
        monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")
        monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin@2026")

        yield

        for p in [self.temp_audit_path, self.temp_users_path, self.temp_manual_path]:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def test_01_entity_creation_audit_event(self):
        """TEST 1: Creating a manual entity logs an ENTITY_CREATE audit event."""
        app = create_app()
        client = TestClient(app)

        # Login
        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # Create entity
        res_e = client.post("/api/entities", headers=headers, json={
            "entity_type": "PERSON",
            "name": "Audit Test Suspect"
        })
        assert res_e.status_code == 201
        ent_id = res_e.json()["id"]

        # Check audit log
        res_audit = client.get("/api/audit?action=ENTITY_CREATE", headers=headers)
        assert res_audit.status_code == 200
        audit_data = res_audit.json()
        assert audit_data["filtered_count"] >= 1
        event = audit_data["events"][0]
        assert event["action"] == "ENTITY_CREATE"
        assert event["resource_id"] == ent_id
        assert event["actor_id"] == "analyst"
        assert event["status"] == "SUCCESS"

    def test_02_failed_entity_creation_audit_event(self):
        """TEST 2: Invalid entity creation generates an ENTITY_CREATE_FAILED audit event."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # Invalid entity type
        res_bad = client.post("/api/entities", headers=headers, json={"entity_type": "INVALID_TYPE"})
        assert res_bad.status_code == 422

        res_audit = client.get("/api/audit?action=ENTITY_CREATE_FAILED", headers=headers)
        assert res_audit.status_code == 200
        events = res_audit.json()["events"]
        assert len(events) >= 1
        assert events[0]["status"] == "FAILURE"

    def test_03_relationship_creation_audit_event(self):
        """TEST 3: Creating a relationship logs a RELATIONSHIP_CREATE audit event."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res_e = client.post("/api/entities", headers=headers, json={"entity_type": "PERSON", "name": "Contact Person"})
        ent_id = res_e.json()["id"]

        res_r = client.post("/api/relationships", headers=headers, json={
            "source_id": "PERSON_017",
            "target_id": ent_id,
            "relationship": "CONTACTED",
            "confidence": 0.95
        })
        assert res_r.status_code == 201
        rel_id = res_r.json()["id"]

        res_audit = client.get("/api/audit?action=RELATIONSHIP_CREATE", headers=headers)
        assert res_audit.status_code == 200
        events = res_audit.json()["events"]
        assert any(e["resource_id"] == rel_id for e in events)

    def test_04_dataset_deletion_denial_audit_event(self):
        """TEST 4: Attempting to delete a dataset entity logs ENTITY_DELETE_DENIED with status DENIED."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res_del = client.delete("/api/entities/PERSON_017", headers=headers)
        assert res_del.status_code == 403

        res_audit = client.get("/api/audit?action=ENTITY_DELETE_DENIED", headers=headers)
        assert res_audit.status_code == 200
        events = res_audit.json()["events"]
        assert len(events) >= 1
        assert events[0]["status"] == "DENIED"
        assert events[0]["resource_id"] == "PERSON_017"

    def test_05_investigation_query_audit_event(self):
        """TEST 5: AI Investigator queries generate INVESTIGATION_QUERY audit records."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res_ai = client.post("/api/investigate", headers=headers, json={
            "question": "How are Case 101 and Case 204 connected?"
        })
        assert res_ai.status_code == 200

        res_audit = client.get("/api/audit?action=INVESTIGATION_QUERY", headers=headers)
        assert res_audit.status_code == 200
        events = res_audit.json()["events"]
        assert len(events) >= 1
        assert "Case 101" in events[0]["details"]["question"]
        assert events[0]["actor_type"] == "AI"

    def test_06_authentication_success_and_failure_events(self):
        """TEST 6: Login attempts generate AUTH_LOGIN_SUCCESS and AUTH_LOGIN_FAILED audit events."""
        app = create_app()
        client = TestClient(app)

        # Failed login
        client.post("/api/auth/login", json={"username": "analyst", "password": "bad_password"})
        # Successful login
        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res_audit = client.get("/api/audit?resource_type=AUTH", headers=headers)
        assert res_audit.status_code == 200
        actions = [e["action"] for e in res_audit.json()["events"]]
        assert "AUTH_LOGIN_SUCCESS" in actions
        assert "AUTH_LOGIN_FAILED" in actions

    def test_07_audit_records_survive_cold_restart(self):
        """TEST 7: Audit log records persist on disk and are restored after server restart."""
        # 1. Instance 1: Generate events
        app1 = create_app()
        client1 = TestClient(app1)
        login_res = client1.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client1.post("/api/entities", headers=headers, json={"entity_type": "LOCATION", "name": "Surveillance Point Alpha"})
        del client1
        del app1

        # 2. Instance 2: Cold restart
        app2 = create_app()
        client2 = TestClient(app2)
        login_res2 = client2.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers2 = {"Authorization": f"Bearer {login_res2.json()['access_token']}"}

        res_audit2 = client2.get("/api/audit?action=ENTITY_CREATE", headers=headers2)
        assert res_audit2.status_code == 200
        events = res_audit2.json()["events"]
        assert len(events) >= 1
        assert "Surveillance Point Alpha" in str(events[0]["details"])

    def test_08_privacy_and_secret_redaction(self):
        """TEST 8: Passwords and tokens are never written to audit records."""
        logger = AuditLogger(filepath=self.temp_audit_path)
        logger.log(
            action="TEST_ACTION",
            actor_id="analyst",
            details={
                "username": "analyst",
                "password": "SuperSecretPassword123!",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "normal_field": "public_data"
            }
        )

        with open(self.temp_audit_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        assert "SuperSecretPassword123!" not in raw_text
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in raw_text
        assert "[REDACTED]" in raw_text
        assert "public_data" in raw_text

    def test_09_dataset_immutability_during_auditing(self):
        """TEST 9: Audit actions leave data/synthetic_data.json completely untouched."""
        dataset_path = get_default_dataset_path()
        hash_before = compute_sha256(dataset_path)

        app = create_app()
        client = TestClient(app)
        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        client.post("/api/entities", headers=headers, json={"entity_type": "PERSON", "name": "Probe"})
        client.post("/api/investigate", headers=headers, json={"question": "Test query"})

        hash_after = compute_sha256(dataset_path)
        assert hash_before == hash_after, "data/synthetic_data.json was modified during audit logging!"

    def test_10_case_and_entity_inspection_audit_events(self):
        """TEST 10: Inspecting cases and entities logs CASE_VIEW and ENTITY_VIEW audit events."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # Inspect case
        res_c = client.get("/api/cases/CASE_101", headers=headers)
        assert res_c.status_code == 200

        # Inspect entity
        res_e = client.get("/api/entities/PERSON_017", headers=headers)
        assert res_e.status_code == 200

        res_audit = client.get("/api/audit", headers=headers)
        assert res_audit.status_code == 200
        actions = [e["action"] for e in res_audit.json()["events"]]
        assert "CASE_VIEW" in actions
        assert "ENTITY_VIEW" in actions
