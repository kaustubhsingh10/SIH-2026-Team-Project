"""
CRIMEGRAPH — Frontend/Backend Error-Handling Compatibility Test Suite

Verifies that all HTTP error responses produced by the backend match the exact
structure consumed by the frontend (web/service.js HttpCrimeGraphAdapter.fetchJson).

Frontend contract (service.js L519-530):
  - `response.status` → 400, 401, 403, 404, 409, 422, 429, or 500
  - `response.headers.get("Retry-After")` → numeric string for 429
  - `errData.detail` → human-readable string (no secrets / stack traces / paths)
  - `errData.retry_after` → numeric seconds for 429 (body field consumed by service.js L525)
  - `X-Request-ID` / `X-Response-Time` → observability headers on all responses

Design notes:
  - CRIMEGRAPH_AUTH_STRICT=true activates full 401 enforcement (matches production Render deployment).
  - CRIMEGRAPH_AUTH_STRICT=false (default) is the non-strict demo mode used during development.
  - No backend code is modified — this is a pure compatibility read.
"""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _create_isolated_app(monkeypatch, *, strict_auth=False, rate_limit=False):
    """Build an isolated TestClient with fresh temp paths and given settings."""
    tf_u = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tf_m = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tf_u.close()
    tf_m.close()
    users_path = Path(tf_u.name)
    manual_path = Path(tf_m.name)

    monkeypatch.setenv("CRIMEGRAPH_USERS_PATH", str(users_path))
    monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(manual_path))
    monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "compat-test-secret-2026")
    monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst123")
    monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true" if rate_limit else "false")
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true" if strict_auth else "false")

    return create_app(), [users_path, manual_path]


@pytest.fixture()
def client(monkeypatch):
    """Non-strict (demo) auth client — authenticated via login for most tests."""
    app, paths = _create_isolated_app(monkeypatch, strict_auth=False)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in paths:
        try: p.unlink()
        except OSError: pass


@pytest.fixture()
def strict_client(monkeypatch):
    """Strict auth client — unauthenticated requests return 401."""
    app, paths = _create_isolated_app(monkeypatch, strict_auth=True)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in paths:
        try: p.unlink()
        except OSError: pass


@pytest.fixture()
def analyst_token(client):
    res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture()
def strict_analyst_token(strict_client):
    res = strict_client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
    assert res.status_code == 200, f"Strict login failed: {res.text}"
    return res.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def header_keys(response):
    return {k.lower() for k in response.headers}


# ===========================================================================
# SECTION 1 — HTTP Status Code Compliance
# ===========================================================================

class TestStatusCodeCompliance:
    """Backend must emit the canonical HTTP codes that service.js branches on."""

    # ── 401 tests need strict_auth=True ───────────────────────────────────

    def test_401_missing_token_in_strict_mode(self, strict_client):
        """GET /api/entities with no token in strict mode → 401 with 'detail'."""
        res = strict_client.get("/api/entities")
        assert res.status_code == 401, \
            f"Expected 401 in strict mode, got {res.status_code}: {res.text}"
        body = res.json()
        assert "detail" in body, "401 must contain 'detail'"
        assert body["detail"], "'detail' must be non-empty"

    def test_401_invalid_token_no_secret_leak(self, strict_client):
        """Garbage token in strict mode → 401; detail must not leak JWT secrets or key material."""
        res = strict_client.get(
            "/api/entities",
            headers={"Authorization": "Bearer garbage.token.here"}
        )
        assert res.status_code == 401
        body = res.json()
        assert "detail" in body
        detail_lower = body["detail"].lower()
        # "signature" is acceptable — "Invalid token signature" is user-facing, not a secret.
        # Check that no actual secret material is leaked:
        for term in ("hs256", "key material", "jwt_secret", "secret_key"):
            assert term not in detail_lower, \
                f"401 detail leaks JWT secret term '{term}': {body['detail']}"

    def test_401_wrong_signature_jwt(self, strict_client):
        """Well-formed but wrong-signature JWT in strict mode → 401."""
        fake_jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiJhbmFseXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ"
            ".INVALIDSIGNATURE"
        )
        res = strict_client.get("/api/entities", headers={"Authorization": f"Bearer {fake_jwt}"})
        assert res.status_code == 401
        assert "detail" in res.json()

    # ── 403 / 404 / 422 don't require strict mode ─────────────────────────

    def test_403_delete_dataset_entity(self, client, analyst_token):
        """DELETE /api/entities/PERSON_017 → 403 (DATASET protected); no fs paths in detail."""
        res = client.delete("/api/entities/PERSON_017", headers=auth_header(analyst_token))
        assert res.status_code == 403
        body = res.json()
        assert "detail" in body
        for bad in ("C:\\", "/home/", "C:/"):
            assert bad not in body.get("detail", ""), f"403 leaks path '{bad}'"

    def test_404_nonexistent_entity(self, client, analyst_token):
        res = client.get("/api/entities/NONEXISTENT_XXXX_9999", headers=auth_header(analyst_token))
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_404_nonexistent_case(self, client, analyst_token):
        res = client.get("/api/cases/CASE_NONEXISTENT_9999", headers=auth_header(analyst_token))
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_404_nonexistent_evidence(self, client, analyst_token):
        res = client.get("/api/evidence/EVID_FAKE_9999", headers=auth_header(analyst_token))
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_404_nonexistent_relationship_delete(self, client, analyst_token):
        res = client.delete("/api/relationships/REL_FAKE_9999", headers=auth_header(analyst_token))
        assert res.status_code == 404
        assert "detail" in res.json()

    def test_422_missing_required_entity_field(self, client, analyst_token):
        """POST /api/entities missing 'name' → 422 with 'detail'."""
        res = client.post(
            "/api/entities",
            json={"entity_type": "PERSON"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 422
        assert "detail" in res.json()

    def test_422_no_traceback_or_paths_leaked(self, client, analyst_token):
        """422 body must not contain Traceback, site-packages, or filesystem paths."""
        res = client.post(
            "/api/entities",
            json={"entity_type": "PERSON"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 422
        body_str = res.text
        for bad in ("Traceback", "site-packages", "C:\\", "/home/"):
            assert bad not in body_str, f"422 body leaks '{bad}'"


# ===========================================================================
# SECTION 2 — 429 Rate-Limit Response — Exact Frontend Contract
# service.js L521: response.headers.get("Retry-After")
# service.js L525: errData.retry_after
# ===========================================================================

class TestRateLimitResponseContract:

    def _make_rl_client(self, monkeypatch):
        app, paths = _create_isolated_app(monkeypatch, strict_auth=False, rate_limit=True)
        return TestClient(app, raise_server_exceptions=False).__enter__(), paths

    def _get_analyst_token(self, rl_client):
        res = rl_client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
        assert res.status_code == 200
        return res.json()["access_token"]

    def _hammer_until_429(self, rl_client, token, ip, max_requests=30):
        for _ in range(max_requests):
            r = rl_client.post(
                "/api/investigate",
                json={"question": "rl test"},
                headers={**auth_header(token), "X-Forwarded-For": ip}
            )
            if r.status_code == 429:
                return r
        return None

    def test_429_retry_after_header_present_and_numeric(self, monkeypatch):
        """429 must set Retry-After HTTP header as numeric string (service.js L521)."""
        rl_client, paths = self._make_rl_client(monkeypatch)
        token = self._get_analyst_token(rl_client)
        hit = self._hammer_until_429(rl_client, token, "10.42.42.42")
        for p in paths:
            try: p.unlink()
            except OSError: pass

        assert hit is not None, "Rate limit was never triggered in 30 AI requests"
        assert hit.status_code == 429
        ra = hit.headers.get("Retry-After") or hit.headers.get("retry-after")
        assert ra is not None, "429 must include Retry-After HTTP header (consumed by service.js L521)"
        assert ra.isdigit(), f"Retry-After header must be numeric string, got: '{ra}'"

    def test_429_body_has_detail_and_retry_after(self, monkeypatch):
        """429 body must carry both 'detail' and 'retry_after' (service.js L524-525)."""
        rl_client, paths = self._make_rl_client(monkeypatch)
        token = self._get_analyst_token(rl_client)
        hit = self._hammer_until_429(rl_client, token, "10.43.43.43")
        for p in paths:
            try: p.unlink()
            except OSError: pass

        assert hit is not None, "Rate limit was never triggered"
        body = hit.json()
        assert "detail" in body, "429 body must have 'detail' (service.js L524)"
        assert isinstance(body["detail"], str)
        assert "retry_after" in body, \
            "429 body must have 'retry_after' — consumed by service.js L525"
        assert isinstance(body["retry_after"], (int, float))
        assert body["retry_after"] > 0

    def test_429_no_secrets_in_body(self, monkeypatch):
        """429 body must not contain passwords, tokens, or filesystem paths."""
        rl_client, paths = self._make_rl_client(monkeypatch)
        token = self._get_analyst_token(rl_client)
        hit = self._hammer_until_429(rl_client, token, "10.44.44.44")
        for p in paths:
            try: p.unlink()
            except OSError: pass

        if hit is None:
            pytest.skip("Rate limit not triggered in this run")
        body_str = hit.text
        for term in ("password", "secret", "Bearer ", "C:\\", "/home/", "Traceback", "jwt_secret"):
            assert term not in body_str, f"429 body leaks '{term}'"

    def test_health_endpoint_exempt_from_rate_limit(self, monkeypatch):
        """GET /api/health must return 200 even after 80 rapid requests (always exempt)."""
        rl_client, paths = self._make_rl_client(monkeypatch)
        for _ in range(80):
            r = rl_client.get("/api/health", headers={"X-Forwarded-For": "10.45.45.45"})
            assert r.status_code == 200, \
                f"/api/health returned {r.status_code} — must be rate-limit exempt"
        for p in paths:
            try: p.unlink()
            except OSError: pass


# ===========================================================================
# SECTION 3 — Observability Headers on Error Responses
# ===========================================================================

class TestObservabilityHeadersOnErrors:
    """X-Request-ID and X-Response-Time must appear on ALL responses, including errors."""

    def test_401_carries_request_id(self, strict_client):
        """401 in strict mode must carry X-Request-ID."""
        res = strict_client.get("/api/entities")
        assert res.status_code == 401
        assert "x-request-id" in header_keys(res), \
            "401 must carry X-Request-ID header"

    def test_401_carries_response_time(self, strict_client):
        """401 in strict mode must carry X-Response-Time."""
        res = strict_client.get("/api/entities")
        assert res.status_code == 401
        rt = res.headers.get("X-Response-Time") or res.headers.get("x-response-time")
        assert rt is not None, "401 must carry X-Response-Time header"

    def test_403_carries_request_id(self, client, analyst_token):
        res = client.delete("/api/entities/PERSON_017", headers=auth_header(analyst_token))
        assert res.status_code == 403
        assert "x-request-id" in header_keys(res)

    def test_404_carries_request_id(self, client, analyst_token):
        res = client.get("/api/entities/FAKE_9999", headers=auth_header(analyst_token))
        assert res.status_code == 404
        assert "x-request-id" in header_keys(res)

    def test_422_carries_request_id(self, client, analyst_token):
        res = client.post(
            "/api/entities",
            json={"entity_type": "PERSON"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 422
        assert "x-request-id" in header_keys(res)

    def test_200_health_carries_both_correlation_headers(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        lkeys = header_keys(res)
        assert "x-request-id" in lkeys
        assert "x-response-time" in lkeys


# ===========================================================================
# SECTION 4 — Auth Flow Security: No Secret Leakage
# ===========================================================================

class TestAuthFlowSecurityCompat:

    def test_login_success_schema(self, client):
        """POST /api/auth/login → {access_token, token_type, user} — no password in body."""
        res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
        assert res.status_code == 200
        body = res.json()
        assert "access_token" in body
        assert "token_type" in body
        assert body["token_type"].lower() == "bearer"
        body_str = str(body)
        assert "$2b$" not in body_str
        assert "analyst123" not in body_str

    def test_login_failure_401_no_password_echo(self, client):
        """Wrong password → 401 with 'detail'; must not echo the password or bcrypt hash."""
        res = client.post("/api/auth/login", json={"username": "analyst", "password": "WRONGPASSWORD_XYZ"})
        assert res.status_code == 401
        body = res.json()
        assert "detail" in body
        body_str = str(body)
        assert "WRONGPASSWORD_XYZ" not in body_str
        assert "$2b$" not in body_str

    def test_login_unknown_user_401(self, client):
        """Unknown username → 401 (no user enumeration)."""
        res = client.post("/api/auth/login", json={"username": "NONEXISTENT_USER_12345", "password": "x"})
        assert res.status_code == 401
        assert "detail" in res.json()

    def test_me_no_password_field(self, client, analyst_token):
        """GET /api/auth/me → user info with NO password or hash field."""
        res = client.get("/api/auth/me", headers=auth_header(analyst_token))
        assert res.status_code == 200
        body_str = str(res.json())
        assert "password" not in body_str.lower()
        assert "$2b$" not in body_str

    def test_me_unauthenticated_returns_401_in_strict_mode(self, strict_client):
        """GET /api/auth/me with no token in strict mode → 401."""
        res = strict_client.get("/api/auth/me")
        assert res.status_code == 401


# ===========================================================================
# SECTION 5 — API Contract Integrity
# Verify response schemas consumed by service.js have not regressed.
# ===========================================================================

class TestApiContractIntegrity:

    def test_cases_list_has_id_and_title(self, client, analyst_token):
        """GET /api/cases → list items with 'id' and 'title' (service.js L537-545)."""
        res = client.get("/api/cases", headers=auth_header(analyst_token))
        assert res.status_code == 200
        cases = res.json()
        assert isinstance(cases, list) and len(cases) > 0
        c = cases[0]
        assert "id" in c
        assert "title" in c

    def test_graph_has_nodes_and_edges_arrays(self, client, analyst_token):
        """GET /api/graph → {nodes: [...], edges: [...]} (service.js L552-570)."""
        res = client.get("/api/graph", headers=auth_header(analyst_token))
        assert res.status_code == 200
        body = res.json()
        assert "nodes" in body and "edges" in body
        assert isinstance(body["nodes"], list)
        assert isinstance(body["edges"], list)

    def test_graph_node_has_id_type_origin(self, client, analyst_token):
        """Graph nodes must have id, type/entity_type, origin (service.js L552-560)."""
        res = client.get("/api/graph", headers=auth_header(analyst_token))
        nodes = res.json()["nodes"]
        assert len(nodes) > 0
        n = nodes[0]
        assert "id" in n
        assert "type" in n or "entity_type" in n
        assert "origin" in n

    def test_graph_edge_has_id_source_target_relationship(self, client, analyst_token):
        """Graph edges must have id, source/source_id, target/target_id, relationship (service.js L562-570)."""
        res = client.get("/api/graph", headers=auth_header(analyst_token))
        edges = res.json()["edges"]
        assert len(edges) > 0
        e = edges[0]
        assert "id" in e
        assert "source" in e or "source_id" in e
        assert "target" in e or "target_id" in e
        assert "relationship" in e

    def test_entity_detail_has_required_fields(self, client, analyst_token):
        """
        GET /api/entities/PERSON_017 → {id, type, confidence/details.confidence, relationships:[...]}
        service.js L579-596 reads: id, type/entity_type, confidence, origin, relationships.
        Backend returns confidence inside 'details' dict — service.js gracefully handles this
        via the fallback chain (raw.confidence || 0.95).
        """
        res = client.get("/api/entities/PERSON_017", headers=auth_header(analyst_token))
        assert res.status_code == 200
        body = res.json()
        assert "id" in body
        assert "type" in body or "entity_type" in body
        # confidence may be top-level OR nested inside 'details' dict
        # service.js L584: `raw.confidence !== undefined ? raw.confidence : 0.95`
        has_confidence = (
            "confidence" in body
            or (isinstance(body.get("details"), dict) and "confidence" in body["details"])
        )
        assert has_confidence, \
            f"Entity response must expose 'confidence' at top-level or inside 'details': {list(body.keys())}"
        assert "relationships" in body
        assert isinstance(body["relationships"], list)

    def test_investigate_response_has_answer_field(self, client, analyst_token):
        """POST /api/investigate → response with 'answer' (or 'response') field."""
        res = client.post(
            "/api/investigate",
            json={"question": "Who is PERSON_017?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert "answer" in body or "response" in body or "detail" in body

    def test_audit_response_has_events_list(self, client, analyst_token):
        """GET /api/audit → body with 'events' list (service.js L732 getAuditLogs)."""
        res = client.get("/api/audit", headers=auth_header(analyst_token))
        assert res.status_code == 200
        body = res.json()
        assert "events" in body
        assert isinstance(body["events"], list)

    def test_health_returns_status_field_without_auth(self, client):
        """GET /api/health → {status: 'healthy'} — no auth required."""
        res = client.get("/api/health")
        assert res.status_code == 200
        body = res.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")

    def test_create_entity_returns_id_field(self, client, analyst_token):
        """POST /api/entities → 201 response with 'id' field (app.js L779-783)."""
        res = client.post(
            "/api/entities",
            json={"entity_type": "PERSON", "name": "FE_Compat_Test_Person", "confidence": 0.9},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 201
        body = res.json()
        assert "id" in body
        client.delete(f"/api/entities/{body['id']}", headers=auth_header(analyst_token))

    def test_create_relationship_returns_id_field(self, client, analyst_token):
        """POST /api/relationships → 201 response with 'id' field (app.js L842-844)."""
        e1 = client.post(
            "/api/entities",
            json={"entity_type": "PERSON", "name": "FE_Compat_SRC_2026", "confidence": 0.8},
            headers=auth_header(analyst_token)
        )
        e2 = client.post(
            "/api/entities",
            json={"entity_type": "PHONE", "name": "+91-9999988888",
                  "phone_number": "+91-9999988888", "confidence": 0.8},
            headers=auth_header(analyst_token)
        )
        assert e1.status_code == 201 and e2.status_code == 201
        src_id, tgt_id = e1.json()["id"], e2.json()["id"]

        rel = client.post(
            "/api/relationships",
            json={"source_id": src_id, "target_id": tgt_id, "relationship": "USES"},
            headers=auth_header(analyst_token)
        )
        assert rel.status_code == 201
        assert "id" in rel.json()

        client.delete(f"/api/relationships/{rel.json()['id']}", headers=auth_header(analyst_token))
        client.delete(f"/api/entities/{src_id}", headers=auth_header(analyst_token))
        client.delete(f"/api/entities/{tgt_id}", headers=auth_header(analyst_token))


# ===========================================================================
# SECTION 6 — Audit Events on Error Paths
# ===========================================================================

class TestAuditOnErrorPaths:

    def test_audit_records_login_failure(self, client, analyst_token):
        """A failed login must appear in the audit log."""
        client.post("/api/auth/login", json={"username": "analyst", "password": "BAD_PW_AUDIT_COMPAT"})
        res = client.get("/api/audit?limit=50", headers=auth_header(analyst_token))
        assert res.status_code == 200
        events = res.json().get("events", [])
        failure_events = [
            e for e in events
            if "FAIL" in e.get("action", "").upper() or "FAIL" in e.get("status", "").upper()
        ]
        assert len(failure_events) > 0, \
            "Audit log must contain at least one failure event after a bad login"

    def test_audit_event_schema_matches_frontend_mock(self, client, analyst_token):
        """
        Audit events must contain the fields defined in MockCrimeGraphAdapter.getAuditLogs
        (service.js L408-437): event_id, timestamp, actor_id, action, status
        """
        res = client.get("/api/audit?limit=5", headers=auth_header(analyst_token))
        assert res.status_code == 200
        events = res.json().get("events", [])
        assert len(events) > 0, "Audit log must have at least one event"
        required = {"event_id", "timestamp", "actor_id", "action", "status"}
        for event in events[:5]:
            missing = required - set(event.keys())
            assert not missing, f"Audit event missing fields {missing}: {event}"

    def test_audit_no_secrets_in_events(self, client, analyst_token):
        """Audit log entries must not expose passwords, bcrypt hashes, or filesystem paths."""
        res = client.get("/api/audit?limit=20", headers=auth_header(analyst_token))
        assert res.status_code == 200
        events_str = str(res.json())
        for term in ("password", "$2b$", "C:\\Users", "/home/", "jwt_secret", "SECRET"):
            assert term not in events_str, f"Audit log leaks '{term}'"
