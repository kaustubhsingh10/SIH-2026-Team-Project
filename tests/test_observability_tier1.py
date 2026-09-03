"""Tier 1 Observability & Production Monitoring Verification Tests for CrimeGraph AI.

Tests:
1. Backend health check availability and metrics inclusion
2. Request correlation ID (X-Request-ID) and latency header (X-Response-Time)
3. Client correlation ID preservation
4. Real-time metrics collector aggregation
5. Unhandled error containment (no stack traces, local paths, or secrets)
6. AI investigation intelligence telemetry tracking
7. Persistence operations telemetry tracking
8. Structured log sanitization and path masking
9. Slow request threshold evaluation
10. Synthetic dataset SHA-256 immutability
"""

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import get_default_dataset_path
from crimegraph.observability.logging import sanitize_log_message
from crimegraph.observability.metrics import metrics


def compute_sha256(filepath: Path) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestTier1Observability:

    @pytest.fixture(autouse=True)
    def setup_observability_env(self, monkeypatch):
        """Isolates testing environment and temporary storage."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_audit:
            self.temp_audit_path = Path(tf_audit.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_users:
            self.temp_users_path = Path(tf_users.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_manual:
            self.temp_manual_path = Path(tf_manual.name)

        monkeypatch.setenv("CRIMEGRAPH_AUDIT_LOG_PATH", str(self.temp_audit_path))
        monkeypatch.setenv("CRIMEGRAPH_USERS_PATH", str(self.temp_users_path))
        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(self.temp_manual_path))
        monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "obs-test-key-2026")
        monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")
        monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin@2026")
        monkeypatch.setenv("SLOW_REQUEST_THRESHOLD_MS", "100.0")

        yield

        for p in [self.temp_audit_path, self.temp_users_path, self.temp_manual_path]:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def test_01_health_check_availability_and_metrics(self):
        """TEST 1: /api/health returns healthy and supports diagnostics."""
        app = create_app()
        client = TestClient(app)

        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json() == {"status": "healthy"}

        # With metrics query param
        res_diag = client.get("/api/health?metrics=true")
        assert res_diag.status_code == 200
        data = res_diag.json()
        assert data["status"] == "healthy"
        assert "diagnostics" in data
        assert "uptime_seconds" in data["diagnostics"]
        assert "total_requests" in data["diagnostics"]

    def test_02_request_correlation_and_latency_headers(self):
        """TEST 2: Every API response includes X-Request-ID and X-Response-Time."""
        app = create_app()
        client = TestClient(app)

        res = client.get("/")
        assert res.status_code == 200
        assert "X-Request-ID" in res.headers
        assert res.headers["X-Request-ID"].startswith("req_")
        assert "X-Response-Time" in res.headers
        assert res.headers["X-Response-Time"].endswith("ms")

    def test_03_forwarded_request_id_preservation(self):
        """TEST 3: Client supplied X-Request-ID is preserved across processing."""
        app = create_app()
        client = TestClient(app)

        custom_id = "test-client-corr-id-9988"
        res = client.get("/api/health", headers={"X-Request-ID": custom_id})
        assert res.status_code == 200
        assert res.headers["X-Request-ID"] == custom_id

    def test_04_metrics_collector_aggregation(self):
        """TEST 4: MetricsCollector tracks request counts and route latencies."""
        app = create_app()
        client = TestClient(app)

        client.get("/")
        client.get("/api/health")

        summary = metrics.get_summary()
        assert summary["total_requests"] >= 2
        assert "GET /api/health" in summary["route_performance"]

    def test_05_error_response_no_traceback_or_paths(self):
        """TEST 5: Unhandled exceptions return safe 500 without tracebacks or paths."""
        app = create_app()
        
        @app.get("/api/test-error")
        def trigger_error():
            raise RuntimeError("Simulated failure at C:\\Users\\admin\\app.py")

        client = TestClient(app, raise_server_exceptions=False)
        res = client.get("/api/test-error")
        assert res.status_code == 500
        content = res.json()
        assert "detail" in content
        assert "traceback" not in str(content).lower()
        assert "c:\\" not in str(content).lower()
        assert "/users/" not in str(content).lower()
        assert "X-Request-ID" in res.headers

    def test_06_ai_investigator_telemetry(self):
        """TEST 6: AI investigation requests record intelligence telemetry."""
        app = create_app()
        client = TestClient(app)

        # Login
        r_auth = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {r_auth.json()['access_token']}"}

        initial_ai_queries = metrics.get_summary()["ai_intelligence"]["total_queries"]

        res = client.post("/api/investigate", headers=headers, json={
            "question": "How are Case 101 and Case 204 connected?"
        })
        assert res.status_code == 200

        summary = metrics.get_summary()
        assert summary["ai_intelligence"]["total_queries"] > initial_ai_queries
        assert summary["ai_intelligence"]["confidence_tiers"]["HIGH"] >= 1

    def test_07_persistence_telemetry(self):
        """TEST 7: Manual data saves increment persistence telemetry metrics."""
        app = create_app()
        client = TestClient(app)

        r_auth = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {r_auth.json()['access_token']}"}

        initial_saves = metrics.get_summary()["persistence"]["successful_saves"]

        res = client.post("/api/entities", headers=headers, json={
            "entity_type": "PERSON",
            "name": "Telemetry Test Entity"
        })
        assert res.status_code == 201

        summary = metrics.get_summary()
        assert summary["persistence"]["successful_saves"] > initial_saves

    def test_08_log_sanitization_privacy(self):
        """TEST 8: Passwords, tokens, and local file paths are sanitized from logs."""
        raw_log = "User logged in with password='SecretPassword123' token=Bearer eyJhbGciOi... path=C:\\Users\\admin\\repo\\file.py"
        clean_log = sanitize_log_message(raw_log)

        assert "SecretPassword123" not in clean_log
        assert "eyJhbGciOi" not in clean_log
        assert "C:\\Users" not in clean_log
        assert "[REDACTED]" in clean_log

    def test_09_metrics_endpoint_readiness(self):
        """TEST 9: GET /api/metrics provides operational dashboard data."""
        app = create_app()
        client = TestClient(app)

        res = client.get("/api/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "route_performance" in data
        assert "ai_intelligence" in data
        assert "persistence" in data

    def test_10_dataset_immutability(self):
        """TEST 10: data/synthetic_data.json hash strictly preserved."""
        dataset_path = get_default_dataset_path()
        initial_hash = compute_sha256(dataset_path)

        app = create_app()
        client = TestClient(app)

        client.get("/")
        client.get("/api/health")
        client.get("/api/metrics")

        final_hash = compute_sha256(dataset_path)
        assert initial_hash == final_hash, "data/synthetic_data.json was modified!"
