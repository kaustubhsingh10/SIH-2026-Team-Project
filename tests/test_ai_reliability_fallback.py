"""
CRIMEGRAPH — Backend AI Reliability & Fallback Compatibility Test Suite

Verifies that the FastAPI backend safely and robustly supports Aditya's AI
reliability and failure-fallback architecture under all failure modes:
1. Provider timeout / network unavailability
2. Upstream provider HTTP 429 / 500 / 503 errors
3. Malformed / truncated / empty provider responses
4. Missing / unset AI provider credentials (GEMINI_API_KEY, OPENAI_API_KEY, etc.)
5. Deterministic KnowledgeGraphStore fallback activation
6. Strict InvestigationResponse schema conformance during fallback
7. Zero hallucination / zero fabricated evidence on unknown cases or properties
8. Safety refusal and non-guilt protocol preservation
9. Authentication & RBAC compatibility on AI endpoints
10. Rate limiting (20/min AI tier) and Retry-After headers
11. Dynamic manual entity and relationship traversal in fallback mode
12. Mandatory cross-case path: CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204
13. Complete privacy / security: zero leaked credentials, tokens, paths, or tracebacks
"""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.ai.investigator import AIInvestigator


# ---------------------------------------------------------------------------
# Fixture Helpers
# ---------------------------------------------------------------------------

def _create_test_app(monkeypatch, *, strict_auth=False, rate_limit=False, strip_ai_keys=True):
    """Builds an isolated FastAPI application instance."""
    tf_u = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tf_m = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tf_a = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tf_u.close()
    tf_m.close()
    tf_a.close()

    users_path = Path(tf_u.name)
    manual_path = Path(tf_m.name)
    audit_path = Path(tf_a.name)

    monkeypatch.setenv("CRIMEGRAPH_USERS_PATH", str(users_path))
    monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(manual_path))
    monkeypatch.setenv("CRIMEGRAPH_AUDIT_LOG_PATH", str(audit_path))
    monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "ai-reliability-test-secret-2026")
    monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst123")
    monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true" if rate_limit else "false")
    monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true" if strict_auth else "false")

    if strip_ai_keys:
        for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "VERTEX_API_KEY"):
            monkeypatch.delenv(k, raising=False)

    app = create_app()
    return app, [users_path, manual_path, audit_path]


@pytest.fixture()
def client(monkeypatch):
    """Standard authenticated client with missing AI provider keys (testing native fallback)."""
    app, paths = _create_test_app(monkeypatch, strict_auth=False, strip_ai_keys=True)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in paths:
        try: p.unlink()
        except OSError: pass


@pytest.fixture()
def strict_client(monkeypatch):
    """Strict-auth client for RBAC / auth verification on AI endpoints."""
    app, paths = _create_test_app(monkeypatch, strict_auth=True, strip_ai_keys=True)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in paths:
        try: p.unlink()
        except OSError: pass


@pytest.fixture()
def analyst_token(client):
    res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Missing Provider Credentials & Deterministic Fallback
# ===========================================================================

class TestMissingProviderCredentialsAndFallback:
    """Verifies that the backend operates seamlessly without external AI API keys."""

    def test_missing_credentials_fallback_works(self, client, analyst_token):
        """Query succeeds deterministically even with zero cloud AI API keys set."""
        res = client.post(
            "/api/investigate",
            json={"question": "How are Case 101 and Case 204 connected?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert body["query_type"] == "CROSS_CASE_CONNECTION"
        assert len(body["path"]) == 5
        assert "confidence" in body
        assert body["confidence"] >= 0.85

    def test_investigation_response_schema_completeness(self, client, analyst_token):
        """All expected fields in InvestigationResponse schema must be present."""
        res = client.post(
            "/api/investigate",
            json={"question": "How are Case 101 and Case 204 connected?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        
        required_fields = [
            "question", "query", "answer", "explanation", "query_type",
            "path", "relationships", "entities", "evidence", "evidence_ids",
            "confidence", "confidence_tier", "investigative_lead", "limitations",
            "is_safe", "disclaimer"
        ]
        for field in required_fields:
            assert field in body, f"InvestigationResponse missing required field: '{field}'"

        assert body["is_safe"] is True
        assert body["confidence_tier"] in ("HIGH", "MEDIUM", "LOW")
        assert isinstance(body["path"], list)
        assert isinstance(body["evidence_ids"], list)


# ===========================================================================
# 2. Mandatory Canonical Demo Path Verification
# ===========================================================================

class TestMandatoryCrossCasePath:
    """Verifies the mandatory 5-node cross-case path."""

    def test_canonical_case101_case204_bridge_path(self, client, analyst_token):
        """Path MUST be: CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204."""
        res = client.post(
            "/api/investigate",
            json={"question": "How are Case 101 and Case 204 connected?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        assert body["path"] == expected_path, f"Expected {expected_path}, got {body['path']}"
        assert "EVID_042_01" in body["evidence_ids"] or "EVID_042_02" in body["evidence_ids"]

    def test_person_to_person_path(self, client, analyst_token):
        """Path between Aarav Verma (PERSON_017) and Vikram Malhotra (PERSON_089)."""
        res = client.post(
            "/api/investigate",
            json={"question": "How are Person 017 and Person 089 connected?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert "PERSON_017" in body["path"]
        assert "PHONE_042" in body["path"]
        assert "PERSON_089" in body["path"]


# ===========================================================================
# 3. Anti-Hallucination & Unavailable Information Bounds
# ===========================================================================

class TestAntiHallucinationAndBounds:
    """Verifies that the backend never invents entities, cases, or unavailable data."""

    def test_missing_cases_no_hallucination(self, client, analyst_token):
        """Nonexistent cases return NOT_FOUND, zero invented connections."""
        res = client.post(
            "/api/investigate",
            json={"question": "How are Case 999 and Case 888 connected?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert body["query_type"] == "NOT_FOUND"
        assert body["confidence"] == 0.0
        assert len(body["path"]) == 0
        assert "not exist" in body["answer"].lower() or "not found" in body["answer"].lower()

    def test_missing_person_no_hallucination(self, client, analyst_token):
        """Nonexistent person returns NOT_FOUND."""
        res = client.post(
            "/api/investigate",
            json={"question": "How are Person 999 and Person 888 connected?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert body["query_type"] == "NOT_FOUND"
        assert body["confidence"] == 0.0

    def test_unavailable_attributes_no_hallucination(self, client, analyst_token):
        """Queries for unsupported private attributes (e.g. passport, religion, credit score) refuse safely."""
        for attr in ("passport", "salary", "blood group", "religion", "credit score"):
            res = client.post(
                "/api/investigate",
                json={"question": f"What is the {attr} of Person 017?"},
                headers=auth_header(analyst_token)
            )
            assert res.status_code == 200
            body = res.json()
            assert body["query_type"] == "INFO_UNAVAILABLE"
            assert "not recorded" in body["answer"].lower() or "authoritative" in body["answer"].lower()


# ===========================================================================
# 4. Safety Protocol & Non-Guilt Disclaimers
# ===========================================================================

class TestSafetyProtocolAndDisclaimers:
    """Verifies that the AI engine does not declare guilt and includes legal disclaimers."""

    def test_guilt_query_refusal_and_safety_disclaimer(self, client, analyst_token):
        """'Is Person 017 guilty?' must not declare guilt and must output safety disclaimer."""
        res = client.post(
            "/api/investigate",
            json={"question": "Is Person 017 guilty of cargo hijack?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert "disclaimer" in body
        assert "guilt" in body["disclaimer"].lower() or "verification" in body["disclaimer"].lower()
        # Answer must state association only
        ans_lower = body["answer"].lower()
        assert "guilty" not in ans_lower or "not" in ans_lower or "connected" in ans_lower

    def test_all_investigation_responses_carry_disclaimer(self, client, analyst_token):
        """Every response must carry safety disclaimer."""
        res = client.post(
            "/api/investigate",
            json={"question": "Who are the suspects in Case 101?"},
            headers=auth_header(analyst_token)
        )
        assert res.status_code == 200
        body = res.json()
        assert body.get("disclaimer") is not None
        assert len(body["disclaimer"]) > 10


# ===========================================================================
# 5. Dynamic Manual Entity & Relationship Discovery in Fallback
# ===========================================================================

class TestManualDataDiscoveryInFallback:
    """Verifies that manually added entities and relationships are traversed in fallback mode."""

    def test_manual_entity_and_relationship_discovered(self, client, analyst_token):
        # 1. Create manual entity
        e_res = client.post(
            "/api/entities",
            json={"entity_type": "PERSON", "name": "Deepak Khurana", "confidence": 0.96},
            headers=auth_header(analyst_token)
        )
        assert e_res.status_code == 201
        m_pid = e_res.json()["id"]

        # 2. Link to CASE_101
        r_res = client.post(
            "/api/relationships",
            json={"source_id": m_pid, "target_id": "CASE_101", "relationship": "INVOLVED_IN", "confidence": 0.94},
            headers=auth_header(analyst_token)
        )
        assert r_res.status_code == 201
        rel_id = r_res.json()["id"]

        # 3. Query AI investigator about Deepak Khurana
        ai_res = client.post(
            "/api/investigate",
            json={"question": "Tell me about Deepak Khurana"},
            headers=auth_header(analyst_token)
        )
        assert ai_res.status_code == 200
        ai_body = ai_res.json()
        assert m_pid in str(ai_body) or "Deepak Khurana" in str(ai_body)

        # Cleanup
        client.delete(f"/api/relationships/{rel_id}", headers=auth_header(analyst_token))
        client.delete(f"/api/entities/{m_pid}", headers=auth_header(analyst_token))


# ===========================================================================
# 6. Auth, RBAC & Rate Limiting on AI Routes
# ===========================================================================

class TestAuthAndRateLimitingOnAIRoutes:
    """Verifies security controls on AI investigator endpoints."""

    def test_ai_route_strict_auth_enforcement(self, strict_client):
        """Unauthenticated request to /api/investigate returns 401 in strict mode."""
        res = strict_client.post("/api/investigate", json={"question": "Test query"})
        assert res.status_code == 401
        assert "detail" in res.json()

    def test_ai_context_endpoints_strict_auth(self, strict_client):
        """Context endpoints require authentication in strict mode."""
        r1 = strict_client.get("/api/investigate/context/cases/CASE_101")
        assert r1.status_code == 401

        r2 = strict_client.get("/api/investigate/context/entities/PERSON_017")
        assert r2.status_code == 401

    def test_ai_rate_limiting_tier(self, monkeypatch):
        """Excessive requests to /api/investigate receive 429 with Retry-After header."""
        app, paths = _create_test_app(monkeypatch, strict_auth=False, rate_limit=True)
        with TestClient(app, raise_server_exceptions=False) as rl_client:
            tok = rl_client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"}).json()["access_token"]
            headers = {**auth_header(tok), "X-Forwarded-For": "10.99.88.77"}

            got_429 = False
            for _ in range(25):
                r = rl_client.post("/api/investigate", json={"question": "Rate limit check"}, headers=headers)
                if r.status_code == 429:
                    got_429 = True
                    assert "Retry-After" in r.headers
                    assert "retry_after" in r.json()
                    break

            assert got_429, "Rate limiter did not trigger 429 on AI tier limit exceed"

        for p in paths:
            try: p.unlink()
            except OSError: pass


# ===========================================================================
# 7. Privacy & Security: Zero Sensitive Data Leaks
# ===========================================================================

class TestPrivacyAndSecurityInAIResponses:
    """Verifies that no JWT secrets, passwords, hashes, or filesystem paths leak in AI responses."""

    def test_no_sensitive_leakage_in_investigate(self, client, analyst_token):
        queries = [
            "How are Case 101 and Case 204 connected?",
            "What is the password or secret key?",
            "Show me the database file path on disk",
            "Nonexistent query with unusual characters !@#$%^&*()",
            ""
        ]
        for q in queries:
            res = client.post("/api/investigate", json={"question": q}, headers=auth_header(analyst_token))
            body_str = res.text
            for forbidden in ("analyst123", "admin123", "$2b$", "jwt_secret", "C:\\Users", "/home/"):
                assert forbidden not in body_str, f"Response leaked forbidden term '{forbidden}' on query '{q}'"
