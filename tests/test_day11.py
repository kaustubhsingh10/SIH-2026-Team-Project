"""Day 11 Tests — Backend Deployment Readiness, Reproducibility, and Final Demo Integrity.

Tests specifically designed for Day 11 requirements:
1. Environment template validation (.env.example)
2. Synthetic demo dataset determinism & reproducibility
3. Full API readiness across all contract endpoints
4. Clean lifecycle & state preservation
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset, get_default_dataset_path
from crimegraph.graph.traversal import find_cross_case_connections


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestDeploymentAndConfiguration:
    """Verifies deployment configuration and reproducibility assets."""

    def test_env_example_exists_and_safe(self):
        env_example_path = Path(".env.example")
        assert env_example_path.exists()
        content = env_example_path.read_text(encoding="utf-8")
        assert "HOST=" in content
        assert "PORT=" in content
        assert "CORS_ORIGINS=" in content
        # Ensure no real secrets/keys are in template
        assert "sk-" not in content
        assert "password" not in content.lower() or "placeholder" in content.lower()

    def test_dataset_path_resolution(self):
        dataset_path = get_default_dataset_path()
        assert dataset_path.exists()
        assert dataset_path.suffix == ".json"

    def test_dataset_reproducibility(self):
        # Verify multiple reloads yield identical node, edge, and evidence counts
        store1 = load_dataset()
        store2 = load_dataset()
        assert len(store1.entities) == len(store2.entities)
        assert len(store1.relationships) == len(store2.relationships)
        assert len(store1.evidence) == len(store2.evidence)
        assert len(store1.get_entities_by_type("CASE")) == len(store2.get_entities_by_type("CASE"))


class TestFullDemoAPISurface:
    """Smoke test ensuring every single API contract endpoint is ready for demonstration."""

    def test_api_surface_readiness(self, client):
        # 1. System
        assert client.get("/").status_code == 200
        assert client.get("/api/health").status_code == 200

        # 2. Cases
        assert client.get("/api/cases").status_code == 200
        assert client.get("/api/cases/CASE_101").status_code == 200
        assert client.get("/api/cases/CASE_101/graph").status_code == 200
        assert client.get("/api/cases/CASE_101/entities").status_code == 200
        assert client.get("/api/cases/CASE_101/timeline").status_code == 200
        assert client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204").status_code == 200

        # 3. Entities
        assert client.get("/api/entities").status_code == 200
        assert client.get("/api/entities/PERSON_017").status_code == 200
        assert client.get("/api/entities/PERSON_017/neighbors").status_code == 200

        # 4. Graph & Paths
        assert client.get("/api/graph").status_code == 200
        assert client.get("/api/paths?source_id=PERSON_017&target_id=PERSON_089").status_code == 200

        # 5. Evidence
        assert client.get("/api/evidence").status_code == 200
        assert client.get("/api/evidence/EVID_042_01").status_code == 200

        # 6. AI & Investigation
        r_inv = client.post("/api/investigate", json={"question": "How are Case 101 and Case 204 connected?"})
        assert r_inv.status_code == 200
        assert r_inv.json()["query_type"] == "CROSS_CASE_CONNECTION"

        # 7. Entity resolution
        assert client.get("/api/entity-resolution/pending").status_code == 200
