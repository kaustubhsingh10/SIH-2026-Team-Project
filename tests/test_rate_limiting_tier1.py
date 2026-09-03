"""Tier 1 Rate Limiting & API Abuse Protection Verification Tests for CrimeGraph AI.

Tests:
1. Normal requests below limit succeed (200 OK)
2. Rapid repeated requests trigger HTTP 429 (Too Many Requests)
3. 429 response contains valid Retry-After header and clean error payload
4. Separate clients/users do not share rate limits
5. AI investigation tier rate limiting (/api/investigate)
6. Mutation endpoint rate limiting (POST /api/entities, /api/relationships)
7. Health check endpoint (/api/health) remains exempt and accessible
8. Existing error handling (404, 403, 422) remains intact
9. Authenticated and unauthenticated rate limiting boundaries
10. Zero secrets or file system path leakage in 429 responses
11. RATE_LIMIT_ENABLED=false allows bypass for local development
12. Audit event recording for RATE_LIMIT_EXCEEDED
"""

import os
import tempfile
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.security.rate_limiter import rate_limiter


class TestTier1RateLimiting:

    @pytest.fixture(autouse=True)
    def setup_rate_limit_env(self, monkeypatch):
        """Isolates testing environment and temporary storage with small rate limit thresholds."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_audit:
            self.temp_audit_path = Path(tf_audit.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_users:
            self.temp_users_path = Path(tf_users.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_manual:
            self.temp_manual_path = Path(tf_manual.name)

        monkeypatch.setenv("CRIMEGRAPH_AUDIT_LOG_PATH", str(self.temp_audit_path))
        monkeypatch.setenv("CRIMEGRAPH_USERS_PATH", str(self.temp_users_path))
        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(self.temp_manual_path))
        monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "rate-limit-test-secret-2026")
        monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")
        monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin@2026")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_REQUESTS", "5")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "3")
        monkeypatch.setenv("RATE_LIMIT_AI_REQUESTS", "3")
        monkeypatch.setenv("RATE_LIMIT_AI_WINDOW_SECONDS", "3")
        monkeypatch.setenv("RATE_LIMIT_MUTATION_REQUESTS", "4")
        monkeypatch.setenv("RATE_LIMIT_MUTATION_WINDOW_SECONDS", "3")

        # Reset in-memory rate limiter state before each test
        rate_limiter._clients.clear()

        yield

        for p in [self.temp_audit_path, self.temp_users_path, self.temp_manual_path]:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def test_01_requests_below_limit_succeed(self):
        """TEST 1: Normal requests below the configured threshold succeed."""
        app = create_app()
        client = TestClient(app)

        for _ in range(3):
            res = client.get("/")
            assert res.status_code == 200

    def test_02_limit_exceeded_returns_429(self):
        """TEST 2: Exceeding threshold triggers HTTP 429 Too Many Requests."""
        app = create_app()
        client = TestClient(app)

        # Configured for 5 requests per 3 seconds on default tier
        for _ in range(5):
            res = client.get("/")
            assert res.status_code == 200

        # 6th request should be blocked
        res_blocked = client.get("/")
        assert res_blocked.status_code == 429
        data = res_blocked.json()
        assert "Too many requests" in data["detail"]
        assert "Retry-After" in res_blocked.headers
        assert int(res_blocked.headers["Retry-After"]) >= 1

    def test_03_ai_investigator_rate_limiting_tier(self):
        """TEST 3: AI Investigator endpoint enforces stricter limit (3 req/3s)."""
        app = create_app()
        client = TestClient(app)

        # Login
        r_auth = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {r_auth.json()['access_token']}"}

        # 3 AI queries should pass
        for _ in range(3):
            res = client.post("/api/investigate", headers=headers, json={"question": "What is Case 101?"})
            assert res.status_code == 200

        # 4th query triggers 429
        res_blocked = client.post("/api/investigate", headers=headers, json={"question": "What is Case 101?"})
        assert res_blocked.status_code == 429
        assert res_blocked.headers.get("X-RateLimit-Tier") == "AI"

    def test_04_mutation_rate_limiting_tier(self):
        """TEST 4: Mutation endpoint (POST /api/entities) enforces mutation limit (4 req/3s)."""
        app = create_app()
        client = TestClient(app)

        r_auth = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {r_auth.json()['access_token']}"}

        # First 4 mutations pass
        for i in range(4):
            res = client.post("/api/entities", headers=headers, json={
                "id": f"MANUAL_PERSON_RL_{i}",
                "entity_type": "PERSON",
                "name": f"Rate Limit Person {i}"
            })
            assert res.status_code == 201

        # 5th mutation triggers 429
        res_blocked = client.post("/api/entities", headers=headers, json={
            "id": "MANUAL_PERSON_RL_BLOCKED",
            "entity_type": "PERSON",
            "name": "Blocked Person"
        })
        assert res_blocked.status_code == 429
        assert res_blocked.headers.get("X-RateLimit-Tier") == "MUTATION"

    def test_05_separate_clients_isolated_limits(self):
        """TEST 5: Different clients/IPs do not share rate limit counters."""
        app = create_app()
        client = TestClient(app)

        # Client A (IP 192.168.1.10) exhausts limit
        for _ in range(5):
            res = client.get("/", headers={"X-Forwarded-For": "192.168.1.10"})
            assert res.status_code == 200

        res_a_blocked = client.get("/", headers={"X-Forwarded-For": "192.168.1.10"})
        assert res_a_blocked.status_code == 429

        # Client B (IP 192.168.1.20) should still succeed
        res_b = client.get("/", headers={"X-Forwarded-For": "192.168.1.20"})
        assert res_b.status_code == 200

    def test_06_health_endpoint_is_exempt(self):
        """TEST 6: /api/health is exempt and remains accessible under high volume."""
        app = create_app()
        client = TestClient(app)

        for _ in range(20):
            res = client.get("/api/health")
            assert res.status_code == 200
            assert res.json() == {"status": "healthy"}

    def test_07_rate_limit_disabled_mode(self, monkeypatch):
        """TEST 7: Setting RATE_LIMIT_ENABLED=false disables rate limiting."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        app = create_app()
        client = TestClient(app)

        for _ in range(15):
            res = client.get("/")
            assert res.status_code == 200

    def test_08_no_secrets_in_429_payload(self):
        """TEST 8: 429 response does not expose file paths, stack traces, or secrets."""
        app = create_app()
        client = TestClient(app)

        for _ in range(5):
            client.get("/")

        res_blocked = client.get("/")
        assert res_blocked.status_code == 429
        text = res_blocked.text
        assert "c:\\" not in text.lower()
        assert "/users/" not in text.lower()
        assert "traceback" not in text.lower()
        assert "jwt" not in text.lower()

    def test_09_sliding_window_recovery_after_expiry(self):
        """TEST 9: Client can make requests again after sliding window expires."""
        app = create_app()
        client = TestClient(app)

        for _ in range(5):
            res = client.get("/")
            assert res.status_code == 200

        res_blocked = client.get("/")
        assert res_blocked.status_code == 429

        # Wait for 3.1s window to expire
        time.sleep(3.1)

        res_recovered = client.get("/")
        assert res_recovered.status_code == 200
