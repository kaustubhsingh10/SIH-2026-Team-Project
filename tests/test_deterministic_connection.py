"""Test suite for Prompt #3: Deterministic Data Connection & Architecture Rules."""

import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from crimegraph.api.app import create_app
from crimegraph.data.loader import load_dataset, get_default_dataset_path
from crimegraph.graph.store import KnowledgeGraphStore


class TestDeterministicDataConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = TestClient(cls.app)

    def test_01_backend_health_check(self):
        """Verify GET /api/health returns healthy status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_02_canonical_dataset_file_exists(self):
        """Verify canonical dataset file exists at data/synthetic_data.json."""
        path = get_default_dataset_path()
        self.assertTrue(path.exists(), f"Canonical dataset path {path} does not exist!")

    def test_03_missing_dataset_in_production_raises_error(self):
        """Verify missing dataset raises FileNotFoundError when allow_generate=False."""
        bogus_path = Path("data/non_existent_file_9999.json")
        with self.assertRaises(FileNotFoundError):
            load_dataset(bogus_path, allow_generate=False)

    def test_04_frontend_service_js_deterministic_config(self):
        """Verify web/service.js implements explicit mode selection and no silent mock fallback."""
        service_js_path = Path(__file__).resolve().parent.parent / "web" / "service.js"
        self.assertTrue(service_js_path.exists(), "web/service.js does not exist!")
        content = service_js_path.read_text(encoding="utf-8")

        # 1. Base URL resolution
        self.assertIn("function getApiBaseUrl()", content)

        # 2. Explicit data mode selection
        self.assertIn("CRIMEGRAPH_DATA_MODE", content)

        # 3. HttpCrimeGraphAdapter active in API mode
        self.assertIn("HttpCrimeGraphAdapter", content)

        # 4. Status badge update
        self.assertIn("LIVE API | CONNECTED", content)
        self.assertIn("LIVE API | OFFLINE", content)

    def test_05_frontend_config_js_data_mode(self):
        """Verify web/config.js defines DATA_MODE configuration."""
        config_js_path = Path(__file__).resolve().parent.parent / "web" / "config.js"
        self.assertTrue(config_js_path.exists(), "web/config.js does not exist!")
        content = config_js_path.read_text(encoding="utf-8")
        self.assertIn("DATA_MODE", content)

    def test_06_fastapi_web_mount(self):
        """Verify FastAPI serves /web/index.html cleanly."""
        response = self.client.get("/web/index.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("CrimeGraph AI", response.text)


if __name__ == "__main__":
    unittest.main()
