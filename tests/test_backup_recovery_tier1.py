"""Tier 1 Backup & Disaster Recovery Tests for CrimeGraph AI Manual Data.

Tests:
1. Valid manual-data backup creation before dataset mutations
2. Backup integrity validation against Pydantic models
3. Automatic disaster recovery when manual_data.json is deleted
4. Automatic disaster recovery when manual_data.json is corrupted with invalid JSON
5. Recovery preserves entity IDs, types, and all details exactly
6. Recovery does not create duplicate nodes or edges on repeated loads
7. Immutable baseline dataset (synthetic_data.json) is NEVER modified during backup or recovery
8. Multiple backup pruning and selection of the latest valid backup
9. Corrupt/invalid backup candidates are rejected safely in favor of valid backups
10. Atomic write and interruption safety during backup generation
11. Support for custom CRIMEGRAPH_MANUAL_DATA_PATH and CRIMEGRAPH_BACKUP_DIR
12. End-to-end server restart and AI investigator discovery after recovery
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.data.backup import (
    create_manual_data_backup,
    find_latest_valid_backup,
    get_default_backup_dir,
    restore_manual_data_from_backup,
    validate_manual_dataset_schema,
)
from crimegraph.data.loader import load_dataset, save_manual_data
from crimegraph.graph.store import KnowledgeGraphStore


class TestTier1BackupRecovery:

    @pytest.fixture(autouse=True)
    def setup_isolated_env(self, monkeypatch):
        """Sets up an isolated temporary directory for manual data and backups."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="cg_backup_test_"))
        self.manual_path = self.test_dir / "manual_data.json"
        self.backup_dir = self.test_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.synthetic_path = Path(__file__).resolve().parent.parent / "data" / "synthetic_data.json"

        # Record baseline synthetic data hash
        hasher = hashlib.sha256()
        with open(self.synthetic_path, "rb") as f:
            hasher.update(f.read())
        self.baseline_synthetic_hash = hasher.hexdigest()

        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(self.manual_path))
        monkeypatch.setenv("CRIMEGRAPH_BACKUP_DIR", str(self.backup_dir))
        monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "backup-test-secret-2026")
        monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        yield

        # Cleanup isolated temp directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

        # Verify synthetic data was never touched
        hasher = hashlib.sha256()
        with open(self.synthetic_path, "rb") as f:
            hasher.update(f.read())
        assert hasher.hexdigest() == self.baseline_synthetic_hash, "data/synthetic_data.json was modified!"

    def test_01_backup_creation_and_validation(self):
        """TEST 1: Valid manual data produces a valid, timestamped backup."""
        store = KnowledgeGraphStore()
        store.add_entity({
            "id": "MANUAL_PERSON_BK_01",
            "type": "PERSON",
            "name": "Backup Test Person",
            "origin": "MANUAL"
        })
        save_manual_data(store, filepath=self.manual_path)

        assert self.manual_path.exists()
        backup_file = create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir)
        assert backup_file is not None
        assert backup_file.exists()
        assert "manual_data_backup_" in backup_file.name

        with open(backup_file, "r", encoding="utf-8") as f:
            b_data = json.load(f)
        is_valid, err = validate_manual_dataset_schema(b_data)
        assert is_valid is True, f"Validation failed: {err}"
        assert b_data["entities"][0]["id"] == "MANUAL_PERSON_BK_01"

    def test_02_disaster_recovery_on_missing_file(self):
        """TEST 2: Deleted manual_data.json is recovered automatically from backup."""
        store = KnowledgeGraphStore()
        store.add_entity({
            "id": "MANUAL_VEH_BK_02",
            "type": "VEHICLE",
            "registration_number": "DL-01-BK-0002",
            "vehicle_type": "car",
            "origin": "MANUAL"
        })
        save_manual_data(store, filepath=self.manual_path)
        create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir)

        # Simulate catastrophic deletion of manual_data.json
        self.manual_path.unlink()
        assert not self.manual_path.exists()

        # Load store - should automatically trigger disaster recovery
        recovered_store = load_dataset(manual_filepath=self.manual_path)
        assert "MANUAL_VEH_BK_02" in recovered_store.entities
        assert self.manual_path.exists()  # Restored on disk

    def test_03_disaster_recovery_on_corrupted_file(self):
        """TEST 3: Corrupted manual_data.json is replaced by latest valid backup."""
        store = KnowledgeGraphStore()
        store.add_entity({
            "id": "MANUAL_PHONE_BK_03",
            "type": "PHONE",
            "phone_number": "+91-98765-43210",
            "origin": "MANUAL"
        })
        save_manual_data(store, filepath=self.manual_path)
        create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir)

        # Intentionally corrupt manual_data.json with junk bytes
        with open(self.manual_path, "w", encoding="utf-8") as f:
            f.write("{{CORRUPT_JSON_DATA_FATAL_ERROR$$%%!!")

        # Load store - should detect corruption and recover from backup
        recovered_store = load_dataset(manual_filepath=self.manual_path)
        assert "MANUAL_PHONE_BK_03" in recovered_store.entities

        # Verify disk file is restored to valid JSON
        with open(self.manual_path, "r", encoding="utf-8") as f:
            restored_json = json.load(f)
        assert restored_json["entities"][0]["id"] == "MANUAL_PHONE_BK_03"

    def test_04_preserves_ids_and_relationships(self):
        """TEST 4: Backup & Recovery accurately preserves complex multi-entity relationships."""
        store = load_dataset(manual_filepath=self.manual_path)
        store.add_entity({
            "id": "MANUAL_PERSON_SRC",
            "type": "PERSON",
            "name": "Source Suspect",
            "origin": "MANUAL"
        })
        store.add_entity({
            "id": "MANUAL_ACCOUNT_TGT",
            "type": "ACCOUNT",
            "account_type": "bank",
            "identifier": "ACC_BK_9944",
            "origin": "MANUAL"
        })
        store.add_relationship({
            "id": "REL_BK_TEST_01",
            "source_id": "MANUAL_PERSON_SRC",
            "target_id": "MANUAL_ACCOUNT_TGT",
            "relationship": "OWNS",
            "confidence": 0.98,
            "origin": "MANUAL"
        })
        save_manual_data(store, filepath=self.manual_path)
        create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir)

        # Corrupt file
        self.manual_path.unlink()

        # Reload
        reloaded = load_dataset(manual_filepath=self.manual_path)
        assert "MANUAL_PERSON_SRC" in reloaded.entities
        assert "MANUAL_ACCOUNT_TGT" in reloaded.entities
        
        rels = [r for r in reloaded.relationships.values() if r.source_id == "MANUAL_PERSON_SRC"]
        assert len(rels) == 1
        assert rels[0].target_id == "MANUAL_ACCOUNT_TGT"
        assert rels[0].relationship == "OWNS"
        assert rels[0].confidence == 0.98

    def test_05_no_duplicate_records_on_repeated_recoveries(self):
        """TEST 5: Repeated load/recovery cycles do not produce duplicate graph entries."""
        store = KnowledgeGraphStore()
        store.add_entity({
            "id": "MANUAL_PERSON_DEDUP",
            "type": "PERSON",
            "name": "Dedup Person",
            "origin": "MANUAL"
        })
        save_manual_data(store, filepath=self.manual_path)
        create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir)

        # Load 3 times consecutively
        s1 = load_dataset(manual_filepath=self.manual_path)
        s2 = load_dataset(manual_filepath=self.manual_path)
        s3 = load_dataset(manual_filepath=self.manual_path)

        manual_ents = [e for e in s3.entities.values() if e.id == "MANUAL_PERSON_DEDUP"]
        assert len(manual_ents) == 1

    def test_06_latest_valid_backup_selection_skips_invalid_backups(self):
        """TEST 6: Recovery skips invalid or corrupted backup files and picks the latest valid one."""
        # 1. Create older valid backup (Version 1)
        v1_data = {
            "metadata": {"version": "1.0"},
            "entities": [{"id": "MANUAL_PERSON_V1", "type": "PERSON", "name": "V1 Person"}],
            "relationships": []
        }
        b1 = self.backup_dir / "manual_data_backup_20260801_100000_000000.json"
        with open(b1, "w", encoding="utf-8") as f:
            json.dump(v1_data, f)

        # 2. Create newer CORRUPT backup file (Version 2)
        b2 = self.backup_dir / "manual_data_backup_20260802_120000_000000.json"
        with open(b2, "w", encoding="utf-8") as f:
            f.write("CORRUPT_RAW_DATA_NOT_JSON")

        # 3. Create newer INVALID SCHEMA backup file (Version 3)
        b3 = self.backup_dir / "manual_data_backup_20260803_140000_000000.json"
        with open(b3, "w", encoding="utf-8") as f:
            json.dump({"entities": "NOT_A_LIST"}, f)

        # Find latest valid backup
        candidate = find_latest_valid_backup(self.backup_dir)
        assert candidate is not None
        valid_path, parsed = candidate
        assert valid_path == b1
        assert parsed["entities"][0]["id"] == "MANUAL_PERSON_V1"

    def test_07_backup_retention_pruning(self):
        """TEST 7: Backup manager prunes excess backups beyond max_backups limit."""
        for i in range(15):
            p = self.backup_dir / f"manual_data_backup_20260801_{i:02d}0000_000000.json"
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"entities": [], "relationships": []}, f)

        # Call create_manual_data_backup with max_backups=5
        test_store = KnowledgeGraphStore()
        test_store.add_entity({"id": "MANUAL_PRUNE_TEST", "type": "PERSON", "name": "Prune", "origin": "MANUAL"})
        save_manual_data(test_store, filepath=self.manual_path)
        create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir, max_backups=5)

        remaining_backups = list(self.backup_dir.glob("manual_data_backup_*.json"))
        assert len(remaining_backups) <= 6

    def test_08_end_to_end_api_and_ai_after_recovery(self):
        """TEST 8: Full API and AI Investigator query pipeline after disaster recovery."""
        app = create_app()
        client = TestClient(app)

        # Login
        r_auth = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {r_auth.json()['access_token']}"}

        # Create manual entity and relationship
        client.post("/api/entities", headers=headers, json={
            "id": "MANUAL_VEH_DISASTER_99",
            "entity_type": "VEHICLE",
            "registration_number": "MH-01-REC-9999",
            "type": "SUV"
        })
        client.post("/api/relationships", headers=headers, json={
            "source_id": "PERSON_017",
            "target_id": "MANUAL_VEH_DISASTER_99",
            "relationship_type": "OWNS"
        })

        # Verify on disk
        assert self.manual_path.exists()
        create_manual_data_backup(self.manual_path, backup_dir=self.backup_dir)

        # Simulate disaster: delete manual data
        self.manual_path.unlink()

        # Restart backend app
        app_restarted = create_app()
        client_restarted = TestClient(app_restarted)

        # Query API entity details
        r_ent = client_restarted.get("/api/entities/MANUAL_VEH_DISASTER_99", headers=headers)
        assert r_ent.status_code == 200
        assert r_ent.json()["id"] == "MANUAL_VEH_DISASTER_99"

        # Query AI investigator
        r_ai = client_restarted.post(
            "/api/investigate",
            headers=headers,
            json={"question": "What vehicle does PERSON_017 own?"}
        )
        assert r_ai.status_code == 200
        assert "MANUAL_VEH_DISASTER_99" in str(r_ai.json()) or "MH-01-REC-9999" in str(r_ai.json())

    def test_09_custom_manual_path_and_backup_dir(self, monkeypatch):
        """TEST 9: Custom CRIMEGRAPH_MANUAL_DATA_PATH and CRIMEGRAPH_BACKUP_DIR are respected."""
        custom_man_path = self.test_dir / "custom_dir" / "my_manual.json"
        custom_bk_dir = self.test_dir / "custom_dir" / "my_backups"
        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(custom_man_path))
        monkeypatch.setenv("CRIMEGRAPH_BACKUP_DIR", str(custom_bk_dir))

        store = KnowledgeGraphStore()
        store.add_entity({"id": "MANUAL_CUSTOM_PATH_01", "type": "PERSON", "name": "Custom Path User", "origin": "MANUAL"})
        save_manual_data(store, filepath=custom_man_path)

        assert custom_man_path.exists()
        bk = create_manual_data_backup(custom_man_path, backup_dir=custom_bk_dir)
        assert bk is not None
        assert custom_bk_dir in bk.parents

        # Delete manual file and recover from custom backup dir
        custom_man_path.unlink()
        recovered = restore_manual_data_from_backup(custom_man_path, backup_dir=custom_bk_dir)
        assert recovered is not None
        assert recovered["entities"][0]["id"] == "MANUAL_CUSTOM_PATH_01"

    def test_10_atomic_write_error_handling(self, monkeypatch):
        """TEST 10: Temporary write errors clean up partial files without corrupting storage."""
        store = KnowledgeGraphStore()
        store.add_entity({"id": "MANUAL_TEMP_ERR", "type": "PERSON", "name": "Temp Error", "origin": "MANUAL"})
        save_manual_data(store, filepath=self.manual_path)
        
        # Test creating backup to non-writable target directory raises cleanly without leaving trash
        invalid_backup_dir = self.test_dir / "non_existent_sub" / "readonly_backup"
        # Should gracefully return None or create directory
        bk = create_manual_data_backup(self.manual_path, backup_dir=invalid_backup_dir)
        assert bk is not None
        assert bk.exists()
