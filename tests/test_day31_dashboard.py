"""Test suite for Day 31 — Investigation Command Dashboard Backend.

Tests cover:
1. Dashboard endpoint health & overall retrieval (GET /api/investigation/dashboard)
2. Case filtering (e.g. GET /api/investigation/dashboard?case_id=CASE_101)
3. Nonexistent case handling (404 Not Found)
4. Summary metric accuracy (total cases, entities, relationships, evidence, patterns)
5. Integration of Day 28 Key Players (NetworkIntelligenceEngine)
6. Integration of Day 29 Path Discovery (AdvancedPathEngine)
7. Integration of Day 30 Suspicious Patterns (SuspiciousPatternEngine)
8. Integration of AI Investigator insights & recommendations
9. Navigation command action links
10. SafetyGuard legal disclaimer compliance
11. RBAC authentication enforcement (401)
"""

import os
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token
from crimegraph.graph.dashboard import InvestigationDashboardService


@pytest.fixture
def test_setup(tmp_path):
    temp_manual = tmp_path / "test_dashboard_manual_data.json"
    os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"] = str(temp_manual)
    os.environ["CRIMEGRAPH_AUTH_STRICT"] = "true"

    app = create_app()
    client = TestClient(app)

    token_analyst, _ = create_access_token(username="analyst", role=UserRole.ANALYST)
    token_admin, _ = create_access_token(username="admin", role=UserRole.ADMIN)

    headers_analyst = {"Authorization": f"Bearer {token_analyst}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    yield {
        "app": app,
        "client": client,
        "headers_analyst": headers_analyst,
        "headers_admin": headers_admin,
    }

    if "CRIMEGRAPH_MANUAL_DATA_PATH" in os.environ:
        del os.environ["CRIMEGRAPH_MANUAL_DATA_PATH"]
    if "CRIMEGRAPH_AUTH_STRICT" in os.environ:
        del os.environ["CRIMEGRAPH_AUTH_STRICT"]


class TestDay31Dashboard:
    """Test suite for Day 31 Investigation Command Dashboard Backend."""

    def test_dashboard_service_retrieval(self, test_setup):
        """Test engine-level dashboard aggregation service."""
        graph = test_setup["app"].state.graph
        service = InvestigationDashboardService(graph)

        res = service.get_dashboard(limit=5)
        assert res.summary.total_cases >= 2
        assert res.summary.total_entities >= 10
        assert res.summary.total_relationships >= 10
        assert res.summary.total_evidence_count >= 5
        assert len(res.cases) >= 1
        assert len(res.key_entities) >= 1
        assert len(res.suspicious_patterns) >= 1
        assert len(res.command_actions) >= 4
        assert "NOT establish legal guilt" in res.safety_notice

    def test_api_get_investigation_dashboard_authenticated(self, test_setup):
        """Test GET /api/investigation/dashboard endpoint."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/investigation/dashboard", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "summary" in data
        assert "cases" in data
        assert "key_entities" in data
        assert "suspicious_patterns" in data
        assert "cross_case_connections" in data
        assert "investigation_paths" in data
        assert "recent_events" in data
        assert "ai_insights" in data
        assert "command_actions" in data
        assert "safety_notice" in data

    def test_api_dashboard_case_filtering(self, test_setup):
        """Test GET /api/investigation/dashboard with case_id=CASE_101 filter."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/investigation/dashboard?case_id=CASE_101", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["case_filter"] == "CASE_101"
        assert len(data["cases"]) == 1
        assert data["cases"][0]["case_id"] == "CASE_101"

    def test_api_dashboard_alias_route(self, test_setup):
        """Test GET /api/dashboard alias route."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/dashboard", headers=headers)
        assert res.status_code == 200
        assert "summary" in res.json()

    def test_dashboard_nonexistent_case_404(self, test_setup):
        """Test 404 response for invalid or missing case ID."""
        client = test_setup["client"]
        headers = test_setup["headers_analyst"]

        res = client.get("/api/investigation/dashboard?case_id=CASE_NONEXISTENT_999", headers=headers)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_dashboard_unauthenticated_request_401(self, test_setup):
        """Test 401 Unauthorized for missing Bearer token."""
        client = test_setup["client"]

        res = client.get("/api/investigation/dashboard")
        assert res.status_code == 401

    def test_dashboard_data_grounding(self, test_setup):
        """Test that all entity and case IDs in dashboard originate from graph store."""
        graph = test_setup["app"].state.graph
        service = InvestigationDashboardService(graph)

        res = service.get_dashboard(limit=5)
        for ke in res.key_entities:
            assert ke.entity_id in graph.entities
        for c in res.cases:
            assert c.case_id in graph.entities
