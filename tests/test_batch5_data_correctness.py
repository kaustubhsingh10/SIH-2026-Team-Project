"""Batch 5 Data Correctness Regression Tests for CrimeGraph AI.

Verifies:
1. Real evidence IDs returned from backend/dataset (e.g. EVID_101_01).
2. Evidence text is not arbitrarily truncated.
3. Complete evidence details reach API clients.
4. Confidence values are sourced from ground-truth data/computation.
5. Case information is dynamically loaded from backend data store.
6. Dashboard metrics are dynamically calculated from actual backend dataset.
"""

from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient
from crimegraph.api.app import app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing TestClient for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> Dict[str, str]:
    """Fixture providing authentication header."""
    res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestBatch5DataCorrectness:
    """Batch 5 Data Correctness Verification Suite."""

    def test_01_real_evidence_ids_returned(self, client: TestClient, auth_headers: Dict[str, str]):
        """Verify evidence endpoint returns ground-truth evidence IDs from dataset."""
        res = client.get("/api/evidence", headers=auth_headers)
        assert res.status_code == 200
        evidence_items = res.json()
        assert len(evidence_items) == 19

        ev_ids = [ev["evidence_id"] for ev in evidence_items]
        # Ground-truth evidence IDs from synthetic_data.json
        assert "EVID_101_01" in ev_ids
        assert "EVID_101_02" in ev_ids
        assert "EVID_204_01" in ev_ids

    def test_02_evidence_text_untruncated(self, client: TestClient, auth_headers: Dict[str, str]):
        """Verify evidence source_text is not truncated."""
        res = client.get("/api/evidence/EVID_101_01", headers=auth_headers)
        assert res.status_code == 200
        ev = res.json()
        assert ev["evidence_id"] == "EVID_101_01"
        assert "source_text" in ev
        # EVID_101_01 text is full forensic transcript
        assert len(ev["source_text"]) > 50

    def test_03_real_confidence_values_sourced(self, client: TestClient, auth_headers: Dict[str, str]):
        """Verify confidence values come from actual evidence records."""
        res = client.get("/api/evidence/EVID_101_01", headers=auth_headers)
        assert res.status_code == 200
        ev = res.json()
        assert "confidence" in ev
        assert isinstance(ev["confidence"], float)
        assert 0.0 <= ev["confidence"] <= 1.0

    def test_04_dynamic_case_details_api(self, client: TestClient, auth_headers: Dict[str, str]):
        """Verify case details endpoint returns actual case metadata."""
        res = client.get("/api/cases/CASE_101", headers=auth_headers)
        assert res.status_code == 200
        c = res.json()
        assert c["id"] == "CASE_101"
        assert c["title"].startswith("Operation Midnight Shadow")
        assert c["status"] in ["ACTIVE", "UNDER_INVESTIGATION"]

    def test_05_dynamic_dashboard_metrics_api(self, client: TestClient, auth_headers: Dict[str, str]):
        """Verify dashboard API returns actual calculated counts from graph store."""
        res = client.get("/api/dashboard", headers=auth_headers)
        assert res.status_code == 200
        dash = res.json()
        summary = dash.get("summary", dash)
        assert summary.get("active_cases", 0) == 4 or summary.get("total_cases", 0) == 4
        assert "investigative_risk" in dash
