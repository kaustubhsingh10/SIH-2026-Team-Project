"""Tier 1 Persistence Verification Tests for CrimeGraph AI.

Tests:
1. Manual entity persistence & cold reload
2. Manual relationship persistence & cold reload
3. Static dataset immutability verification
4. Dataset -> Manual relationship persistence & reload
5. Manual -> Dataset relationship persistence & reload
6. Manual -> Manual relationship persistence & reload
7. Missing persistence file graceful boot
8. Duplicate prevention on multiple reloads
9. Corrupted persistence file safe handling & recovery
10. Atomic persistence file replacement verification
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.loader import (
    get_default_dataset_path,
    get_default_manual_data_path,
    load_dataset,
    save_manual_data,
)
from crimegraph.models.entities import Person, Vehicle
from crimegraph.models.relationships import Relationship, RelationshipType


def _compute_file_hash(filepath: Path) -> str:
    """Computes SHA-256 hash of file content."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestTier1Persistence:

    @pytest.fixture(autouse=True)
    def setup_isolated_storage(self, monkeypatch):
        """Ensures every test runs against an isolated temporary manual storage path."""
        test_dir = tempfile.mkdtemp(prefix="cg_persist_test_")
        self.temp_dir = Path(test_dir)
        self.temp_storage = self.temp_dir / "manual_data.json"

        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(self.temp_storage))
        monkeypatch.setenv("CRIMEGRAPH_BACKUP_DIR", str(self.temp_dir / "backups"))
        yield
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_manual_entity_persistence_and_reload(self):
        """TEST 1: Create manual entity, verify persistence, reload store, verify entity exists."""
        app = create_app()
        client = TestClient(app)

        payload = {
            "entity_type": "PERSON",
            "name": "Arjun Singhal",
            "age": 38,
            "gender": "Male",
            "aliases": ["Singhal"]
        }
        res = client.post("/api/entities", json=payload)
        assert res.status_code == 201
        ent_id = res.json()["id"]

        # Verify disk file is written
        assert self.temp_storage.exists()
        with open(self.temp_storage, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert any(e["id"] == ent_id for e in disk_data.get("entities", []))

        # Cold reload
        app_cold = create_app()
        client_cold = TestClient(app_cold)
        res_get = client_cold.get(f"/api/entities/{ent_id}")
        assert res_get.status_code == 200
        assert res_get.json()["details"]["name"] == "Arjun Singhal"
        assert res_get.json()["details"]["origin"] == "MANUAL"

    def test_02_manual_relationship_persistence_and_reload(self):
        """TEST 2: Create two manual entities and a link, reload, verify both and edge survive."""
        app = create_app()
        client = TestClient(app)

        p = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Operative A"}).json()
        v = client.post("/api/entities", json={"entity_type": "VEHICLE", "registration_number": "KA-01-MM-1122"}).json()

        rel_payload = {
            "source_id": p["id"],
            "target_id": v["id"],
            "relationship": "OWNS",
            "confidence": 0.98
        }
        r_res = client.post("/api/relationships", json=rel_payload)
        assert r_res.status_code == 201
        rel_id = r_res.json()["id"]

        # Cold reload
        app_cold = create_app()
        client_cold = TestClient(app_cold)

        assert client_cold.get(f"/api/entities/{p['id']}").status_code == 200
        assert client_cold.get(f"/api/entities/{v['id']}").status_code == 200

        g_data = client_cold.get("/api/graph").json()
        assert any(e["id"] == rel_id for e in g_data["edges"])

    def test_03_static_dataset_immutability(self):
        """TEST 3: Verify data/synthetic_data.json remains byte-for-byte unmodified after manual mutations."""
        dataset_path = get_default_dataset_path()
        assert dataset_path.exists()
        hash_before = _compute_file_hash(dataset_path)

        app = create_app()
        client = TestClient(app)

        # Create multiple manual entities and links
        p = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Immutability Probe"}).json()
        client.post("/api/relationships", json={
            "source_id": p["id"],
            "target_id": "CASE_101",
            "relationship": "INVOLVED_IN",
            "confidence": 0.95
        })

        hash_after = _compute_file_hash(dataset_path)
        assert hash_before == hash_after, "STATIC DATASET MODIFIED! Immutability constraint violated."

    def test_04_dataset_to_manual_relationship_persistence(self):
        """TEST 4: Create DATASET ENTITY -> MANUAL ENTITY link, verify survival across reload."""
        app = create_app()
        client = TestClient(app)

        v = client.post("/api/entities", json={"entity_type": "VEHICLE", "registration_number": "DL-10-XX-4455"}).json()

        # Connect Dataset Person (PERSON_017) -> Manual Vehicle
        r_res = client.post("/api/relationships", json={
            "source_id": "PERSON_017",
            "target_id": v["id"],
            "relationship": "USES",
            "confidence": 0.96
        })
        assert r_res.status_code == 201
        rel_id = r_res.json()["id"]

        # Cold reload
        app_cold = create_app()
        client_cold = TestClient(app_cold)

        p_details = client_cold.get("/api/entities/PERSON_017").json()
        assert any(r.get("target_id") == v["id"] or r.get("target") == v["id"] for r in p_details["relationships"])

        # Verify AI discovers path
        ai_res = client_cold.post("/api/investigate", json={"question": f"How is PERSON_017 connected to {v['id']}?"})
        assert ai_res.status_code == 200
        assert "PERSON_017" in ai_res.json()["path"] and v["id"] in ai_res.json()["path"]

    def test_05_manual_to_dataset_relationship_persistence(self):
        """TEST 5: Create MANUAL ENTITY -> DATASET ENTITY link, verify survival across reload."""
        app = create_app()
        client = TestClient(app)

        p = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Informant M"}).json()
        r_res = client.post("/api/relationships", json={
            "source_id": p["id"],
            "target_id": "LOC_001",
            "relationship": "SEEN_AT",
            "confidence": 0.91
        })
        assert r_res.status_code == 201
        rel_id = r_res.json()["id"]

        # Cold reload
        app_cold = create_app()
        client_cold = TestClient(app_cold)
        g_data = client_cold.get("/api/graph").json()
        assert any(e["id"] == rel_id and e.get("source_id") == p["id"] and e.get("target_id") == "LOC_001" for e in g_data["edges"])

    def test_06_manual_to_manual_relationship_persistence(self):
        """TEST 6: Create MANUAL ENTITY -> MANUAL ENTITY link, verify survival across reload."""
        app = create_app()
        client = TestClient(app)

        p1 = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Courier One"}).json()
        p2 = client.post("/api/entities", json={"entity_type": "PERSON", "name": "Courier Two"}).json()
        r_res = client.post("/api/relationships", json={
            "source_id": p1["id"],
            "target_id": p2["id"],
            "relationship": "KNOWS",
            "confidence": 0.88
        })
        assert r_res.status_code == 201

        # Cold reload
        app_cold = create_app()
        client_cold = TestClient(app_cold)
        p1_det = client_cold.get(f"/api/entities/{p1['id']}").json()
        assert any(r.get("target_id") == p2["id"] or r.get("target") == p2["id"] for r in p1_det["relationships"])

    def test_07_missing_persistence_file_graceful_boot(self, monkeypatch):
        """TEST 7: Start with non-existent manual file path, verify clean startup without errors."""
        nonexistent_path = self.temp_storage.parent / "nonexistent_sub" / "manual_data.json"
        if nonexistent_path.exists():
            nonexistent_path.unlink()

        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(nonexistent_path))

        store = load_dataset(manual_filepath=nonexistent_path)
        assert len(store.entities) == 34
        assert len(store.relationships) == 24
        assert len(store.get_manual_entities()) == 0

        # Now save something to it — parent directories must be created automatically
        p = Person(id="MANUAL_PERSON_AUTO_DIR", name="Auto Dir Person", origin="MANUAL")
        store.add_entity(p)
        save_manual_data(store, filepath=nonexistent_path)
        assert nonexistent_path.exists()

        if nonexistent_path.exists():
            nonexistent_path.unlink()
            if nonexistent_path.parent.exists():
                nonexistent_path.parent.rmdir()

    def test_08_duplicate_prevention_on_multiple_reloads(self):
        """TEST 8: Repeated loads of store do not duplicate entity or relationship indexes."""
        # Create 1 manual entity and 1 manual relationship
        store = load_dataset(manual_filepath=self.temp_storage)
        p = Person(id="MANUAL_PERSON_DUP_TEST", name="Deduplication Candidate", origin="MANUAL")
        store.add_entity(p)
        rel = Relationship(
            id="REL_MANUAL_DUP_TEST",
            source_id="PERSON_017",
            target_id="MANUAL_PERSON_DUP_TEST",
            relationship=RelationshipType.KNOWS,
            confidence=0.9,
            origin="MANUAL"
        )
        store.add_relationship(rel)
        save_manual_data(store, filepath=self.temp_storage)

        # Load 1
        s1 = load_dataset(manual_filepath=self.temp_storage)
        count_e1 = len(s1.entities)
        count_r1 = len(s1.relationships)
        out_deg_1 = len(s1._outgoing["PERSON_017"])

        # Load 2
        s2 = load_dataset(manual_filepath=self.temp_storage)
        count_e2 = len(s2.entities)
        count_r2 = len(s2.relationships)
        out_deg_2 = len(s2._outgoing["PERSON_017"])

        assert count_e1 == count_e2 == 35
        assert count_r1 == count_r2 == 25
        assert out_deg_1 == out_deg_2

    def test_09_corrupted_persistence_file_safe_handling(self):
        """TEST 9: Malformed/corrupted manual file does not crash the system and baseline loads safely."""
        # Write corrupted JSON
        with open(self.temp_storage, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON CONTENT ... CORRUPT ")

        store = load_dataset(manual_filepath=self.temp_storage)
        assert len(store.entities) == 34
        assert len(store.relationships) == 24
        assert len(store.get_manual_entities()) == 0

    def test_10_atomic_write_verification(self):
        """TEST 10: Verify atomic file replacement produces valid JSON without residual temp files."""
        store = load_dataset(manual_filepath=self.temp_storage)
        p = Person(id="MANUAL_PERSON_ATOMIC", name="Atomic Person", origin="MANUAL")
        store.add_entity(p)
        saved_path = save_manual_data(store, filepath=self.temp_storage)

        assert saved_path.exists()
        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["metadata"]["entity_count"] == 1
        assert data["entities"][0]["id"] == "MANUAL_PERSON_ATOMIC"

        # Ensure no leftover .tmp files
        tmp_files = list(self.temp_storage.parent.glob(f".tmp_{self.temp_storage.name}*"))
        assert len(tmp_files) == 0
